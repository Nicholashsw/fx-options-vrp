/ Load the monthly bar files written by scripts/15_intraday_bars.py into a
/ date-partitioned HDB: one partition per UTC date of the bar's close, table bar
/ (sym, root, time, close, volume), sorted by contract then time, parted on sym.

/   q q/build_hdb.q -bars $FX_VRP_WORK/intraday/bars -hdb $FX_VRP_WORK/intraday/hdb

/ Each month file holds the bars that CLOSE in that month, so no date is split
/ across two files and re-running a month rewrites its partitions cleanly.

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/util.q";
system "l ",.cli.here,"/rv.q";

src:hsym `$.cli.abs .cli.opt`bars;
db:hsym `$.cli.abs .cli.opt`hdb;
files:asc f where (f:key src) like "*.csv";
if[0=count files; -2"no .csv files in ",string src; exit 1];

savedate:{[t;d] `bar set delete dt from select from t where dt=d; .Q.dpft[db;d;`sym;`bar]};

load1:{[f]
  t:("JSSFJ";enlist ",") 0: ` sv src,f;
  t:`time xasc select sym, root, time:.rv.ts ts_ns, close, volume from t;
  t:update dt:"d"$time from t;
  savedate[t] each distinct t`dt;
  -1 string[f],": ",string[count t]," bars, ",string[count distinct t`dt]," dates";
  }

load1 each files;
-1 "hdb written to ",string db;
.cli.done[];
