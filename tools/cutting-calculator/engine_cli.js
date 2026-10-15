"use strict";
/* 從 cutplan_2026-10-15.html（Project 知識庫 claude/cutplan_2026-10-15.html，
   138,434 bytes，SHA-256 cc7058b5…）抽出的引擎函式，逐字複製，未改動邏輯。
   只移除 DOM／UI，並加上 CLI 介面，供與 Python 版交叉比對。

   v2.3.4 對應的範圍（2026-10-15）：
     · packOnce()／packByGroup()：與 09-24 版相同
     · nest()：沿短邊開條時不可轉件被轉 90° 的修正（piecesIn）
     · 刀序與剩料改走 cutplan「固定張數」模式那條路：oldToResult() → mxCutList()／mxRemnants()
       → 多出「修窄」刀與「修窄邊料」
   mxOptimize()（樣板法、補位、REPEAT_TRY）是下一階段（v2.4）的移植範圍，這裡沒有。 */

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
  const piecesIn = pieces;
  const solve = (axes) => {
  let best = null;
  for(const axis of axes){
    const packL = axis === "L" ? uL : uW;
    const packW = axis === "L" ? uW : uL;
    // v2.4 修正：沿短邊開條（axis W）時 pack frame 與板材轉了 90°，
    // 不可轉的零件要先把長寬對調，貼回板材時「長」才會沿板長邊（舊版會把不可轉件轉 90°）
    const pieces = axis === "L" ? piecesIn : piecesIn.map(p => p.rot ? p : {...p, l:p.w, w:p.l});
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
      if(alt.placed > best.placed){ best = alt; }
      else if(alt.placed === best.placed && alt.placed > 0 && alt.sheetsUsed < best.sheetsUsed){ best.alt = alt; }
    }
  }
  return best;
}

/* pack frame → 真實板材座標 */
function mxMap(sheet, x, y, w, h){
  const t = sheet.trim;
  return sheet.ax === "L" ? {x:t + x, y:t + y, w, h} : {x:t + y, y:t + x, w:h, h:w};
}

/* ── 刀序：修邊 → 開條 → 分件 → 修窄 → 補位改切 ── */
function mxCutList(sheet, K, trim){
  const {len, span, ax, board} = sheet;
  const res = sheet.res || 0, tail = res ? 0.5 : K + 0.5;   // 要修邊的板：最後一片後面也要下刀
  const cuts = [];
  let n = 0;
  // meta：說明的結構化資料（k＝說明種類、a＝參數），介面依語言組成文字；note 保留中文給舊程式
  const emit = (phase, kind, pos, a, b, note, meta) => {
    const rowInSheet = (ax === "L") === (kind === "rip");   // rip = pack 的 y=常數線
    cuts.push({n:++n, phase, dir:rowInSheet ? "橫切" : "縱切", kind,
               pos:round1(trim + pos), from:round1(trim + a), to:round1(trim + b), len:round1(b - a), note, meta});
  };
  if(trim > 0){
    cuts.push({n:++n, phase:"修邊", dir:"橫切", kind:"trim", pos:round1(trim), from:0, to:board.L, len:board.L, note:"修下緣基準邊", meta:{k:"trimB", a:[]}});
    cuts.push({n:++n, phase:"修邊", dir:"縱切", kind:"trim", pos:round1(trim), from:0, to:board.W, len:board.W, note:"修左緣基準邊", meta:{k:"trimL", a:[]}});
  }
  const strips = sheet.strips;
  strips.forEach((st, i) => {
    const edge = st.y + st.h;
    if(i < strips.length - 1 || span + res - edge > tail)
      emit("開條", "rip", edge, 0, len + res, `分出第 ${i + 1} 條（條寬 ${round1(st.h)} mm）`, {k:"rip", a:[i + 1, round1(st.h)]});
  });
  strips.forEach((st, i) => {
    st.items.forEach((it, j) => {
      const edge = it.x + it.slotA;
      if(j < st.items.length - 1 || len + res - edge > tail)
        emit("分件", "cross", edge, st.y, st.y + st.h,
             `第 ${i + 1} 條・切在 ${round1(it.slotA)}` + (it.sub ? `（${nameOf(it.host)} 格位）` : ""),
             it.sub ? {k:"crossSub", a:[i + 1, round1(it.slotA)], parts:[2, it.host]} : {k:"cross", a:[i + 1, round1(it.slotA)]});
    });
  });
  strips.forEach((st, i) => {
    st.items.forEach(it => {
      if(st.h - it.cross > 0.5)
        emit("修窄", "rip", st.y + it.cross, it.x, it.x + it.slotA, `第 ${i + 1} 條・${nameOf(it.t)} 修到 ${round1(it.cross)}`, {k:"narrow", a:[i + 1, null, round1(it.cross)], parts:[1, it.t]});
    });
  });
  strips.forEach((st, i) => {
    st.items.forEach(it => {
      if(it.sub && it.slotA - it.along > 0.5)
        emit("補位改切", "cross", it.x + it.along, st.y, st.y + it.cross,
             `第 ${i + 1} 條・${nameOf(it.host)} 格位改切成 ${nameOf(it.t)}`, {k:"subc", a:[i + 1, null, null], parts:[1, it.host, 2, it.t]});
    });
  });
  return cuts;
  function nameOf(t){ return sheet._names ? sheet._names[t] : "件" + (t + 1); }
}

/* ── 剩料：整條、條尾、修窄與改切的邊料（達 minRem 才算可回收） ── */
function mxRemnants(sheet, K, minRem){
  const len = sheet.len + (sheet.res || 0), span = sheet.span + (sheet.res || 0);   // 剩料用整張板量
  const raw = [];
  sheet.strips.forEach((st, i) => {
    const w = len - st.xEnd - K;
    if(w > 0.5) raw.push({x:st.xEnd + K, y:st.y, w, h:st.h, from:`第 ${i + 1} 條尾料`, fk:"tail", fn:i + 1, band:false});
    st.items.forEach(it => {
      const hh = st.h - it.cross - K;
      if(hh > 0.5) raw.push({x:it.x, y:it.y + it.cross + K, w:it.slotA, h:hh, from:`第 ${i + 1} 條修窄邊料`, fk:"narrow", fn:i + 1, band:false});
      if(it.sub){
        const ww = it.slotA - it.along - K;
        if(ww > 0.5) raw.push({x:it.x + it.along + K, y:it.y, w:ww, h:it.cross, from:`第 ${i + 1} 條補位改切邊料`, fk:"subc", fn:i + 1, band:false});
      }
    });
  });
  const rest = span - sheet.usedH - (sheet.strips.length ? K : 0);
  if(rest > 0.5) raw.push({x:0, y:sheet.usedH + K, w:len, h:rest,
                           from:sheet.ax === "W" ? "整條・沿短邊" : "整條・沿長邊", fk:sheet.ax === "W" ? "bandW" : "bandL", fn:0, band:true});
  return raw.map(r => {
    const m = mxMap(sheet, r.x, r.y, r.w, r.h);
    const a = r.w * r.h, dimA = Math.max(r.w, r.h), dimB = Math.min(r.w, r.h);
    return {...m, long:dimA, short:dimB, area:a, cai:a / CAI, from:r.from, fk:r.fk, fn:r.fn, band:r.band,
            usable:dimB >= minRem && dimA >= minRem,
            grade:a >= 300 * 300 ? "A" : a >= 150 * 150 ? "B" : "C"};
  }).filter(r => r.usable || r.band);
}

/* ── 固定張數模式：沿用舊的開條法（單一板型），轉成同一種版面格式 ── */
function oldToResult(parts, res, board, kerf, trim, minRem){
  const T = parts.map((p, i) => ({...p, i, area:p.l * p.w}));
  const idx = new Map(T.map((t, i) => [t.id, i]));
  const names = T.map(t => t.name);
  const sheets = res.sheets.map(sh => ({
    board, ax:res.axis, len:res.packL, span:res.packW, res:board.edgeCut ? kerf : 0, trim, _names:names, usedH:sh.usedH,
    strips:[...sh.strips].sort((a, b) => a.y - b.y).map(st => ({
      y:st.y, h:st.h, xEnd:st.x,
      items:[...st.items].sort((a, b) => a.x - b.x).map(it => ({t:idx.get(it.id), along:it.w, cross:it.h, slotA:it.w, x:it.x, y:it.y, sub:false})),
    })),
  }));
  const miss = new Map();
  res.unplaced.forEach(u => { const k = u.id + "|" + u.why; miss.set(k, {name:u.name, l:u.l, w:u.w, n:(miss.get(k)?.n || 0) + 1, why:u.why}); });
  const cutsAll = sheets.map(s => mxCutList(s, kerf, trim));
  const totalArea = sheets.length * board.L * board.W;
  return {sheets, cutsAll, unplaced:[...miss.values()], T, totalArea, placedArea:res.area, placed:res.placed,
          need:T.reduce((a, t) => a + t.qty, 0), util:totalArea ? res.area / totalArea : 0,
          cuts:cutsAll.reduce((a, c) => a + c.length, 0), method:"固定張數（單一板型開條法）",
          poolSize:0, ms:0, kerf, trim, minRem};
}

/* ── CLI：讀 stdin 的 JSON，輸出正規化結果供比對 ──
   排版用 nest()；刀序與剩料走 cutplan「固定張數」模式的同一條路：oldToResult() → mxCutList()／mxRemnants() */
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const minRemIn = input.minRem === undefined ? 50 : input.minRem;
const res = nest(input.parts, input.sheetL, input.sheetW, input.kerf,
                 input.trim, input.maxSheets || 0, input.remPref || "any", minRemIn);
if(res.error){ console.log(JSON.stringify({error:res.error})); process.exit(0); }
const board = {name:"板", L:input.sheetL, W:input.sheetW};
const out = oldToResult(input.parts, res, board, input.kerf, input.trim, minRemIn);

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
  cuts: out.cutsAll.map(cs => cs.map(c => ({
    n: c.n, phase: c.phase, dir: c.dir, pos: c.pos, from: c.from, to: c.to, len: c.len, note: c.note
  }))),
  remnants: out.sheets.map(sh => mxRemnants(sh, input.kerf, minRemIn)
    .map(r => ({x: round1(r.x), y: round1(r.y), w: round1(r.w), h: round1(r.h),
                long: round1(r.long), short: round1(r.short),
                band: r.band, usable: r.usable, grade: r.grade, from: r.from}))),
};
console.log(JSON.stringify(norm));
