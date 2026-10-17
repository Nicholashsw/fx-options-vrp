/ Replay one month file of bars into the tickerplant in time order, in batches.

/   q q/tick/feed.q -tp localhost:5010 -bars $FX_VRP_WORK/intraday/bars/2024-03.csv [-batch 1000]

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/../util.q";
system "l ",.cli.here,"/../rv.q";

t:("JSSFJ";enlist ",") 0: hsym `$.cli.abs .cli.opt`bars;
t:`time xasc select sym, root, time:.rv.ts ts_ns, close, volume from t;
h:hopen `$":",.cli.optd[`tp;"localhost:5010"];
n:"J"$.cli.optd[`batch;"1000"];
{[h;x] neg[h] (`upd;`bar;x)}[h] each n cut t;
neg[h][];
-1 "sent ",string[count t]," bars";
exit 0;
