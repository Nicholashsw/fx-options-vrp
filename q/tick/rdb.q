/ Real-time subscriber: keeps the session's bars and a running realised variance
/ per contract (live.q), and answers queries against both.

/   q q/tick/rdb.q -p 5011 -tp localhost:5010 -cal $FX_VRP_WORK/intraday/settle_calendar.csv

/ From any q session:  h:hopen 5011; h".live.view[]"

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/../util.q";
system "l ",.cli.here,"/../rv.q";
system "l ",.cli.here,"/../live.q";

.live.cal:asc distinct exec date from ("D";enlist ",") 0: hsym `$.cli.abs .cli.opt`cal;

upd:{[t;x] if[t=`bar; `bar insert x; .live.onbars x];};

.rdb.tp:hopen `$":",.cli.optd[`tp;"localhost:5010"];
bar:.rdb.tp(`.tp.sub;`bar);
-1 "subscribed to bar; query .live.view[] for running volatility";
