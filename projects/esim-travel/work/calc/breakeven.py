import sys,io,contextlib,runpy
import os; buf=io.TextIOWrapper(open(os.devnull,"wb"),encoding="utf-8")
with contextlib.redirect_stdout(buf):
    g=runpy.run_path(sys.argv[1])
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
sc,m=g['sc'],g['model_AB']
fx=83.09
for which in 'AB':
  for k in (0,0.15,0.30):
    best=None
    for c in range(1,200):
      r=m(sc(1,{'cost_usd':c/100,'k':k}),which)['result']
      if r>=0: best=c
    print(which,'k',k,'max ₽/GB wholesale', round(best/100*fx) if best else None, 'B paid' if which=='B' else '', round(best/100*fx*1.6) if best and which=='B' else '')
# pilot: B fixed vs purchases
p=sc(1); e=g['pack_econ'](p,p['b_mult']); print('B cm',round(e['cm']),'cann per', round(m(p,'B')['cann_per']))
