/ A minimal tickerplant: every update is appended to a log (replayable with -11!)
/ and published at once to the subscribers of its table.

/   q q/tick/tick.q -p 5010 [-log tp.log]

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/../util.q";

bar:([] sym:`symbol$(); root:`symbol$(); time:`timestamp$(); close:`float$(); volume:`long$());

.tp.subs:enlist[`]!enlist `int$();
.tp.sub:{[t] if[not t in tables[]; '"no table ",string t]; .tp.subs[t],:.z.w; 0#value t};
.tp.pub:{[t;x] {[t;x;h] neg[h] (`upd;t;x)}[t;x] each .tp.subs t;};
.z.pc:{[h] .tp.subs:.tp.subs except\: h;};

.tp.logf:hsym `$.cli.abs .cli.optd[`log;"tp.log"];
if[not type key .tp.logf; .tp.logf set ()];
.tp.log:hopen .tp.logf;

upd:{[t;x] .tp.log enlist (`upd;t;x); t insert x; .tp.pub[t;x];};

-1 "tickerplant on port ",string[system "p"],", logging to ",string .tp.logf;
