/ Daily realised measures for every futures contract and settlement session.

/   q q/daily_rv.q -hdb $FX_VRP_WORK/intraday/hdb \
/                  -cal $FX_VRP_WORK/intraday/settle_calendar.csv \
/                  -out $FX_VRP_WORK/intraday/rv_daily.csv

/ Runs a month at a time with four days of lead-in, so each month's first session
/ has the previous session's last sample to start its first return from, then
/ keeps the sessions that fall in the month. Output columns:
/   sym session root first_bar last_bar volume n5 rv5 bv5 n1 rv1
/ rv5 and rv1 are sums of squared 5- and 1-minute log returns (daily variance,
/ not annualised); bv5 is bipower variation on the 5-minute grid.

system "l ",{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[],"/util.q";
system "l ",.cli.here,"/rv.q";

calf:hsym `$.cli.abs .cli.opt`cal;
outf:hsym `$.cli.abs .cli.opt`out;
cal:asc distinct exec date from ("D";enlist ",") 0: calf;
system "l ",.cli.abs .cli.opt`hdb;

onemonth:{[m]
  b:select sym, root, time, close, volume from bar where date within (("d"$m)-4;"d"$m+1);
  d:.rv.daily[b;cal];
  r:select from d where m=`month$session;
  -1 string[m],": ",string[count r]," contract-sessions";
  r}

months:asc distinct `month$date;
res:raze onemonth each months;
res:`sym`session xasc select sym, session, root, first_bar, last_bar, volume, n5, rv5, bv5, n1, rv1 from res;
outf 0: csv 0: res;
-1 "wrote ",string[count res]," rows to ",string outf;
.cli.done[];
