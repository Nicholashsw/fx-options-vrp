/ Tests for rv.q and live.q.   q q/tests/test_rv.q

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/../util.q";
system "l ",.cli.here,"/../rv.q";
system "l ",.cli.here,"/../live.q";

.t.pass:0; .t.fail:0;
check:{[name;cond] $[cond; [.t.pass+:1; -1"ok    ",name]; [.t.fail+:1; -2"FAIL  ",name]];};
near:{[a;b] all 1e-12>abs a-b};

/ ---- calendar ------------------------------------------------------------
check["daylight saving 2026 runs 8 March to 1 November"; .rv.dstrange[2026]~2026.03.08 2026.11.01];
check["daylight saving 2017 runs 12 March to 5 November"; .rv.dstrange[2017]~2017.03.12 2017.11.05];
check["2000.01.02 was a Sunday"; 2000.01.02=.rv.nextsun 2000.01.01];
check["summer settlement is 19:00 UTC"; .rv.settletime[2026.07.15]=2026.07.15D19:00:00.000000000];
check["winter settlement is 20:00 UTC"; .rv.settletime[2026.01.15]=2026.01.15D20:00:00.000000000];
check["the Monday after the switch is summer"; .rv.settletime[2026.03.09]=2026.03.09D19:00:00.000000000];
check["the Monday after the switch back is winter"; .rv.settletime[2026.11.02]=2026.11.02D20:00:00.000000000];

cal:2026.07.13 2026.07.14 2026.07.15 2026.07.16 2026.07.17 2026.07.20;
t:2026.07.15D18:55:00.000000000 2026.07.15D19:00:00.000000000 2026.07.15D19:00:00.000000001,
  2026.07.17D21:00:00.000000000 2026.07.19D23:00:00.000000000 2026.07.20D19:01:00.000000000;
check["a bar belongs to the first settlement at or after its close";
  .rv.sessionof[cal;t]~2026.07.15 2026.07.15 2026.07.16 2026.07.20 2026.07.20 0Nd];

/ ---- measures on a known path ---------------------------------------------
/ One contract, a bar every minute from 17:00 to 19:30 UTC on 15 July 2026
/ (settlement 19:00). The 5-minute samples are the closes on the five-minute marks.
ix:til 151;
b:([] sym:151#`A; root:151#`X; time:2026.07.15D17:00:00.000000000+0D00:01:00.000000000*ix;
     close:1.1+0.001*sin 0.37*ix; volume:151#1);
m:.rv.measures[.rv.sample[b;.rv.k5];cal];
c:b[`close] where 0=ix mod 5;                     / closes at 17:00, 17:05, ..., 19:30
r:1_deltas log c;                                    / 30 returns, the first ending 17:05
s15:24#r; s16:24_r;                                  / ending 17:05..19:00 and 19:05..19:30
row:{[m;d] first select from m where session=d};
check["five-minute returns split at settlement: 24 before, 6 after";
  (24 6)~(row[m;2026.07.15]`n;row[m;2026.07.16]`n)];
check["realised variance is the sum of squared returns in the session";
  near[row[m;2026.07.15]`rv;sum s15*s15] and near[row[m;2026.07.16]`rv;sum s16*s16]];
check["the first return of a session starts at the previous session's last sample";
  near[row[m;2026.07.16]`rv;sum {x*x} r 24+til 6]];
check["bipower variation pairs adjacent returns within the session";
  near[row[m;2026.07.15]`bv;(.rv.pi%2)*sum abs[1_s15]*abs -1_s15]];
m1:.rv.measures[.rv.sample[b;.rv.k1];cal];
check["one-minute sampling uses every bar"; 120=row[m1;2026.07.15]`n];

/ A five-day gap drops the return that spans it.
g:([] sym:`B`B`B; root:`X`X`X; time:2026.07.13D15:00:00.000000000 2026.07.13D15:05:00.000000000 2026.07.20D15:00:00.000000000;
     close:1.0 1.01 1.05; volume:1 1 1);
mg:.rv.measures[.rv.sample[g;.rv.k5];cal];
check["a return across more than four days is dropped"; (enlist 1)~exec n from mg];

/ ---- the daily table ------------------------------------------------------
d:.rv.daily[b;cal];
check["daily carries 5- and 1-minute measures for both sessions";
  (2=count d) and all raze not null d[`rv5`rv1`bv5]];
check["daily volume counts bars by session: 17:00-19:00 closes, then 19:01-19:30"; (121 30)~exec volume from d];

/ ---- incremental equals batch ---------------------------------------------
\S 11
n:3000;
rb:([] sym:n?`E`J`N; root:`X; time:asc 2026.07.13D12:00:00.000000000+0D00:00:01.000000000*n?400000;
      close:1+0.01*sums 0.01*-0.5+n?1f; volume:1);
rb:update close:close*exp 0.002*sums -0.5+count[i]?1f by sym from rb;
batch:`sym`session xasc .rv.measures[.rv.sample[rb;.rv.k5];cal];
.live.cal:cal;
.live.onbars rb;
.live.flush[];
live:`sym`session xasc select sym, session, n, rv, bv from 0!.live.acc;
check["running variance after a flush equals the batch measures: keys and counts";
  (select sym, session, n from batch)~select sym, session, n from live];
check["running variance after a flush equals the batch measures: rv and bv";
  near[batch`rv;live`rv] and near[batch`bv;live`bv]];

/ ---- forward windows ------------------------------------------------------
rvd:([] sym:5#`A; session:2026.07.13 2026.07.14 2026.07.15 2026.07.16 2026.07.17;
       rv5:1e-4*1 2 3 4 5f; bv5:1e-4*1 2 3 4 5f; rv1:2e-4*1 2 3 4 5f; n5:5#200);
p:([] row_id:0 1 2; date:2026.07.13 2026.07.15 2026.07.17; sym:`A`A`A; tenor:3 7 3);
f:.rv.forward[rvd;p;0];
check["the window is (t, t+H]: 14th to 16th"; (3=f[0]`n_sessions) and near[f[0]`rv5_sum;9e-4]];
check["a window running past the data takes what exists"; (2=f[1]`n_sessions) and near[f[1]`rv5_sum;9e-4]];
check["annualised as sqrt(252 * mean daily variance)"; near[f[0]`rvol5;sqrt 252*3e-4]];
check["an empty window has no sessions and no volatility"; (0=f[2]`n_sessions) and null f[2]`rvol5];
f2:.rv.forward[update n5:200 50 200 200 200 from rvd;p;100];
check["sessions below the minimum count of returns are left out"; (2=f2[0]`n_sessions) and near[f2[0]`rv5_sum;7e-4]];

-1 string[.t.pass]," passed, ",string[.t.fail]," failed";
exit $[.t.fail;1;0];
