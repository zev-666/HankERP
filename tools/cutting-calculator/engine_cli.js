"use strict";
/* 從 cutplan.html（2026-09-24 版）抽出的引擎函式，逐字複製，未改動邏輯。
   只移除 DOM／UI，並加上 CLI 介面，供與 Python 版交叉比對。 */

const CAI = 300 * 300;
const COLORS = ["#0B6E5F","#C2703B","#3D6CB9","#8A4F9E","#1F8A5B","#B5453C",
                "#2F8C9E","#8B6A1F","#6553B5","#A6455F","#3F7A2E","#96562A"];
const round1 = (v) => Math.round(v*10)/10;

function packOnce(pieces, packL, packW, kerf, sortKey, orient, maxSheets, fitMode){
  const list = pieces.map(p => ({...p}));
  const LONG = (p)=>Math.max(p.l,p.w), SHORT = (p)=>Math.min(p.l,p.w);
  const sorters = {
    height: (a,b)=> (b.h - a.h) || (b.w2 - a.w2),
    area:   (a,b)=> (b.l*b.w - a.l*a.w) || (b.h - a.h),
    long:   (a,b)=> (LONG(b) - LONG(a)) || (SHORT(b) - SHORT(a)),
  };
  for(const p of list){
    if(!p.rot){ p.h = p.w; p.w2 = p.l; p.free = false; }
    else if(orient === "cross"){ p.h = SHORT(p); p.w2 = LONG(p); p.free = false; }
    else if(orient === "along"){ p.h = LONG(p);  p.w2 = SHORT(p); p.free = false; }
    else { p.h = p.w; p.w2 = p.l; p.free = true; }
  }
  list.sort(sorters[sortKey]);

  const sheets = [], unplaced = [];
  const orientationsOf = (p) => {
    let ors;
    if(!p.rot)      ors = [{h:p.w, w:p.l, rotated:false}];
    else if(p.free) ors = [{h:p.w, w:p.l, rotated:false}, {h:p.l, w:p.w, rotated:true}];
    else            ors = [{h:p.h, w:p.w2, rotated: !(p.h === p.w)}];
    return ors.filter(o => o.h <= packW + 1e-9 && o.w <= packL + 1e-9);
  };

  for(const p of list){
    const ors = orientationsOf(p);
    if(!ors.length){ unplaced.push({...p, why:"尺寸超出原板"}); continue; }

    let best = null, newBest = null;
    for(let si=0; si<sheets.length; si++){
      const sh = sheets[si];
      for(let ti=0; ti<sh.strips.length; ti++){
        const st = sh.strips[ti];
        for(const o of ors){
          if(o.h > st.h + 1e-9) continue;
          const x = st.x + (st.items.length ? kerf : 0);
          if(x + o.w > packL + 1e-9) continue;
          const cost = fitMode === "waste"
            ? (st.h - o.h) * o.w
            : (st.h - o.h) * 1e6 + (packL - x - o.w);
          if(!best || cost < best.cost) best = {cost, kind:"strip", si, ti, x, o};
        }
      }
    }
    for(let si=0; si<sheets.length; si++){
      const sh = sheets[si];
      for(const o of ors){
        const y = sh.usedH + (sh.strips.length ? kerf : 0);
        if(y + o.h > packW + 1e-9) continue;
        const cost = fitMode === "waste"
          ? kerf * packL + (packL - o.w) * o.h * 0.5
          : (packW - y - o.h) * 1e3 + (packL - o.w);
        if(!newBest || cost < newBest.cost) newBest = {cost, kind:"newstrip", si, y, o};
      }
    }
    if(fitMode === "waste"){
      if(newBest && (!best || newBest.cost < best.cost)) best = newBest;
    } else if(!best){
      best = newBest;
    }
    if(!best){
      if(maxSheets && sheets.length >= maxSheets){ unplaced.push({...p, why:"板數用盡"}); continue; }
      sheets.push({strips:[], usedH:0});
      best = {kind:"newstrip", si:sheets.length-1, y:0, o:ors[0]};
    }

    const sh = sheets[best.si];
    if(best.kind === "strip"){
      const st = sh.strips[best.ti];
      st.items.push({...p, x:best.x, y:st.y, w:best.o.w, h:best.o.h, rotated:best.o.rotated});
      st.x = best.x + best.o.w;
    } else {
      const st = {y:best.y, h:best.o.h, x:best.o.w, items:[]};
      st.items.push({...p, x:0, y:best.y, w:best.o.w, h:best.o.h, rotated:best.o.rotated});
      sh.strips.push(st);
      sh.usedH = best.y + best.o.h;
    }
  }
  return {sheets, unplaced};
}

function packByGroup(pieces, packL, packW, kerf, maxSheets){
  const groups = new Map();
  for(const p of pieces){
    const key = `${p.l}x${p.w}x${p.rot}`;
    if(!groups.has(key)) groups.set(key, {sample:p, items:[]});
    groups.get(key).items.push(p);
  }
  const plan = [];
  for(const g of groups.values()){
    const p = g.sample, n = g.items.length;
    const cands = [];
    const tryOrient = (h, w, rotated) => {
      if(h > packW + 1e-9 || w > packL + 1e-9) return;
      const perStrip = Math.floor((packL + kerf) / (w + kerf));
      if(perStrip < 1) return;
      const strips = Math.ceil(n / perStrip);
      cands.push({h, w, rotated, perStrip, strips, thickness: strips * (h + kerf)});
    };
    tryOrient(p.w, p.l, false);
    if(p.rot && p.l !== p.w) tryOrient(p.l, p.w, true);
    if(!cands.length){ plan.push({g, impossible:true}); continue; }
    cands.sort((a,b)=> a.thickness - b.thickness || a.strips - b.strips);
    plan.push({g, ...cands[0]});
  }
  plan.sort((a,b) => (b.h||0) - (a.h||0));

  const sheets = [], unplaced = [];
  for(const item of plan){
    if(item.impossible){ item.g.items.forEach(p => unplaced.push({...p, why:"尺寸超出原板"})); continue; }
    let left = [...item.g.items];
    while(left.length){
      const take = left.splice(0, item.perStrip);
      let sh = sheets.find(s => s.usedH + (s.strips.length ? kerf : 0) + item.h <= packW + 1e-9);
      if(!sh){
        if(maxSheets && sheets.length >= maxSheets){ take.forEach(p => unplaced.push({...p, why:"板數用盡"})); continue; }
        sh = {strips:[], usedH:0}; sheets.push(sh);
      }
      const y = sh.usedH + (sh.strips.length ? kerf : 0);
      const st = {y, h:item.h, x:0, items:[]};
      take.forEach((p, i) => {
        const x = i === 0 ? 0 : st.x + kerf;
        st.items.push({...p, x, y, w:item.w, h:item.h, rotated:item.rotated});
        st.x = x + item.w;
      });
      sh.strips.push(st);
      sh.usedH = y + item.h;
    }
  }
  return {sheets, unplaced};
}

function mapRect(res, x, y, w, h){
  const t = res.trim;
  return res.axis === "L"
    ? {x:t + x, y:t + y, w, h}
    : {x:t + y, y:t + x, w:h, h:w};
}

function remnantsOf(sheet, res, minRem){
  const {packL, packW, kerf} = res;
  const raw = [];
  const strips = [...sheet.strips].sort((a,b)=>a.y-b.y);
  strips.forEach((st, i) => {
    const gap = st.items.length ? kerf : 0;
    const w = packL - st.x - gap;
    if(w > 0.5) raw.push({x:st.x + gap, y:st.y, w, h:st.h, from:`第 ${i+1} 條尾料`, band:false});
  });
  const rest = packW - sheet.usedH - (strips.length ? kerf : 0);
  if(rest > 0.5)
    raw.push({x:0, y:sheet.usedH + (strips.length ? kerf : 0), w:packL, h:rest,
              from:res.axis === "W" ? "整條・沿短邊" : "整條・沿長邊", band:true});

  return raw.map(r => {
    const m = mapRect(res, r.x, r.y, r.w, r.h);
    const a = r.w * r.h;
    const dimA = Math.max(m.w, m.h), dimB = Math.min(m.w, m.h);
    return {...m, long:dimA, short:dimB, area:a, cai:a/CAI, from:r.from, band:r.band,
            usable: dimB >= minRem && dimA >= minRem,
            grade: a >= 300*300 ? "A" : a >= 150*150 ? "B" : "C"};
  }).filter(r => r.usable || r.band);
}

function cutList(sheet, res){
  const {packL, packW, trim, kerf, axis} = res;
  const cuts = [];
  let n = 0;
  const emit = (phase, kind, pos, a, b, note) => {
    const isRipRowInSheet = (axis === "L") === (kind === "rip");
    const dir = isRipRowInSheet ? "橫切" : "縱切";
    cuts.push({n:++n, phase, dir, kind,
               pos:round1(trim + pos), from:round1(trim + a), to:round1(trim + b),
               len:round1(b - a), note});
  };

  if(trim > 0){
    cuts.push({n:++n, phase:"修邊", dir:"橫切", kind:"trim", pos:round1(trim), from:0, to:round1(res.sheetL), len:round1(res.sheetL), note:"修下緣基準邊"});
    cuts.push({n:++n, phase:"修邊", dir:"縱切", kind:"trim", pos:round1(trim), from:0, to:round1(res.sheetW), len:round1(res.sheetW), note:"修左緣基準邊"});
  }

  const strips = [...sheet.strips].sort((a,b)=>a.y-b.y);
  strips.forEach((st, i) => {
    const edge = st.y + st.h;
    const isLast = i === strips.length - 1;
    const rest = packW - edge;
    if(!isLast || rest > kerf + 0.5)
      emit("開條", "rip", edge, 0, packL, `分出第 ${i+1} 條（條寬 ${round1(st.h)} mm）`);
  });
  strips.forEach((st, i) => {
    const items = [...st.items].sort((a,b)=>a.x-b.x);
    items.forEach((it, j) => {
      const edge = it.x + it.w;
      const isLast = j === items.length - 1;
      const rest = packL - edge;
      if(!isLast || rest > kerf + 0.5)
        emit("分件", "cross", edge, st.y, st.y + st.h,
             `第 ${i+1} 條・切出 ${it.name} ${round1(it.w)}×${round1(it.h)}`);
    });
  });
  return cuts;
}

function nest(parts, sheetL, sheetW, kerf, trim, maxSheets, remPref, minRem){
  minRem = Number.isFinite(minRem) ? minRem : 50;
  const uL = sheetL - 2*trim, uW = sheetW - 2*trim;
  if(uL <= 0 || uW <= 0) return {error:"修邊量太大，沒有可用區域"};

  const pieces = [];
  parts.forEach((p, i) => {
    for(let k=0; k<p.qty; k++)
      pieces.push({id:p.id, name:p.name, l:p.l, w:p.w, rot:p.rot, color:COLORS[i%COLORS.length]});
  });
  if(!pieces.length) return {error:"沒有有效零件"};

  const wanted = remPref === "strip" ? ["W"] : remPref === "long" ? ["L"] : ["L","W"];
  const other  = remPref === "strip" ? ["L"] : remPref === "long" ? ["W"] : [];

  const solve = (axes) => {
  let best = null;

  for(const axis of axes){
    const packL = axis === "L" ? uL : uW;
    const packW = axis === "L" ? uW : uL;
    for(const sortKey of ["height","long","area"]){
      for(const orient of ["cross","along","free"]){
      for(const fitMode of ["waste","existing","group"]){
        const r = fitMode === "group"
          ? (sortKey === "height" && orient === "cross"
              ? packByGroup(pieces, packL, packW, kerf, maxSheets)
              : null)
          : packOnce(pieces, packL, packW, kerf, sortKey, orient, maxSheets, fitMode);
        if(!r) continue;
        const placed = r.sheets.reduce((s,sh)=>s+sh.strips.reduce((t,st)=>t+st.items.length,0),0);
        const area   = r.sheets.reduce((s,sh)=>s+sh.strips.reduce((t,st)=>t+st.items.reduce((u,it)=>u+it.w*it.h,0),0),0);
        const n = r.sheets.length;
        const cand = {...r, axis, packL, packW, trim, kerf, sheetL, sheetW,
                      placed, area, sheetsUsed:n,
                      util: n ? area/(n*sheetL*sheetW) : 0,
                      strategy:`${axis}/${sortKey}/${orient}/${fitMode}`};

        let bandArea = 0, scraps = 0, cutCount = 0;
        r.sheets.forEach((sh, si) => {
          const stripsN = sh.strips.length;
          const restW = packW - sh.usedH - (stripsN ? kerf : 0);
          const isTail = r.sheets.length > 1 && si === r.sheets.length - 1;
          if(!isTail && restW >= minRem && packL >= minRem) bandArea += restW * packL;
          if(trim > 0) cutCount += 2;
          sh.strips.forEach((st, i) => {
            const stripRest = packW - (st.y + st.h);
            if(i !== stripsN - 1 || stripRest > kerf + 0.5) cutCount++;
            const itemsN = st.items.length;
            st.items.forEach((it, j) => {
              const itemRest = packL - (it.x + it.w);
              if(j !== itemsN - 1 || itemRest > kerf + 0.5) cutCount++;
            });
            const tail = packL - st.x - (st.items.length ? kerf : 0);
            if(tail >= minRem && st.h >= minRem) scraps++;
          });
        });
        cand.bandArea = bandArea; cand.scraps = scraps; cand.cutCount = cutCount;
        cand.byGroup = fitMode === "group";

        if(!best){ best = cand; continue; }
        if(cand.placed !== best.placed){ if(cand.placed > best.placed) best = cand; continue; }
        if(cand.sheetsUsed !== best.sheetsUsed){ if(cand.sheetsUsed < best.sheetsUsed) best = cand; continue; }
        if(Math.abs(cand.util - best.util) > 1e-9){ if(cand.util > best.util) best = cand; continue; }
        if(Math.abs(cand.bandArea - best.bandArea) > 1){ if(cand.bandArea > best.bandArea) best = cand; continue; }
        if(cand.cutCount !== best.cutCount){ if(cand.cutCount < best.cutCount) best = cand; continue; }
        if(cand.scraps < best.scraps) best = cand;
      }
      }
    }
  }
  return best;
  };

  let best = solve(wanted);
  if(best && other.length){
    const alt = solve(other);
    if(alt){
      if(alt.placed > best.placed){
        const forcedFrom = wanted[0];
        best = alt;
        best.forced = {from: forcedFrom, lost: alt.placed - (best.placed - alt.placed)};
        best.forcedFrom = forcedFrom;
      } else if(alt.placed === best.placed && alt.placed > 0 && alt.sheetsUsed < best.sheetsUsed){
        best.alt = alt;
      }
    }
  }
  return best;
}

/* ── CLI：讀 stdin 的 JSON，輸出正規化結果供比對 ── */
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const res = nest(input.parts, input.sheetL, input.sheetW, input.kerf,
                 input.trim, input.maxSheets || 0, input.remPref || "any",
                 input.minRem === undefined ? 50 : input.minRem);
if(res.error){ console.log(JSON.stringify({error:res.error})); process.exit(0); }

const norm = {
  axis: res.axis, strategy: res.strategy,
  sheetsUsed: res.sheetsUsed, placed: res.placed,
  util: Math.round(res.util * 1e9) / 1e9,
  area: round1(res.area),
  bandArea: round1(res.bandArea), scraps: res.scraps, cutCount: res.cutCount,
  unplaced: res.unplaced.length,
  sheets: res.sheets.map(sh => ({
    usedH: round1(sh.usedH),
    strips: sh.strips.map(st => ({
      y: round1(st.y), h: round1(st.h), x: round1(st.x),
      items: st.items.map(it => ({
        id: it.id, x: round1(it.x), y: round1(it.y),
        w: round1(it.w), h: round1(it.h), rotated: it.rotated
      }))
    }))
  })),
  cuts: res.sheets.map(sh => cutList(sh, res).map(c => ({
    n: c.n, phase: c.phase, dir: c.dir, pos: c.pos, from: c.from, to: c.to, len: c.len
  }))),
  remnants: res.sheets.map(sh => remnantsOf(sh, res, input.minRem === undefined ? 50 : input.minRem)
    .map(r => ({x: round1(r.x), y: round1(r.y), w: round1(r.w), h: round1(r.h),
                long: round1(r.long), short: round1(r.short),
                band: r.band, usable: r.usable, grade: r.grade}))),
};
console.log(JSON.stringify(norm));
