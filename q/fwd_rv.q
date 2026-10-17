/ Forward realised volatility per option row from the daily intraday measures,
/ by window join (.rv.forward): for an option on date t with tenor H days, the
/ sessions of its own futures contract in (t, t+H], the window step 10 uses for
/ settlement-based realised volatility.

/   q q/fwd_rv.q -rv $FX_VRP_WORK/intraday/rv_daily.csv \
/                -panel $FX_VRP_WORK/intraday/panel_for_q.csv \
/                -out $FX_VRP_WORK/intraday/fwd_rv.csv [-minn5 100]

/ A session counts only with at least minn5 five-minute returns (default 100 of
/ the roughly 276 in a 23-hour Globex session), which keeps out thin back months.
/ panel_for_q.csv (scripts/16 --export-panel): row_id,date,sym,tenor
/ Output: row_id,n_sessions,rv5_sum,bv5_sum,rv1_sum,n5_sum,rvol5,rvol1

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/util.q";
system "l ",.cli.here,"/rv.q";

rvd:("SDSPPJJFFJF";enlist ",") 0: hsym `$.cli.abs .cli.opt`rv;
p:("JDSJ";enlist ",") 0: hsym `$.cli.abs .cli.opt`panel;
outf:hsym `$.cli.abs .cli.opt`out;
f:.rv.forward[rvd;p;"J"$.cli.optd[`minn5;"100"]];
outf 0: csv 0: f;
-1 "wrote ",string[count f]," rows to ",string outf;
.cli.done[];
