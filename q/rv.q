/ Intraday realised measures for CME FX futures from one-minute bars.
/ Loaded by build_hdb.q, daily_rv.q, tick/rdb.q and tests/test_rv.q.

/ A bar carries its CLOSE time (scripts/15 adds the minute to Databento's open
/ stamp). Bars are sampled every five minutes on the last close in each bucket,
/ and each log return belongs to the settlement session in which it ends, so a
/ session's sum of squared returns runs from one settlement to the next: the same
/ span as the close-to-close settlement return used in step 10.

\d .rv

epoch:946684800000000000;                 / ns from 1970.01.01 to kdb's 2000.01.01
ts:{"p"$x-epoch};                         / unix ns (long) -> timestamp
k5:0D00:05:00.000000000;                  / sampling interval for the headline measures
k1:0D00:01:00.000000000;
gapmax:4D00:00:00.000000000;              / a return spanning a longer gap is dropped
pi:acos -1;

/ First Sunday on or after each date (day 0 of kdb's calendar was a Saturday).
nextsun:{x+(1-("i"$x) mod 7) mod 7};

/ US daylight saving runs from the second Sunday of March to the first Sunday of
/ November. Returns (start;end) for a year, or a pair of lists for a list of years.
dstrange:{[y] m:2000.01m+12*y-2000; (7+nextsun "d"$m+2; nextsun "d"$m+10)};

/ CME FX futures settle at 14:00 Chicago time: 19:00 UTC in summer, 20:00 in winter.
settletime:{[d]
  r:dstrange `year$d;
  ("p"$d)+0D20:00:00.000000000-0D01:00:00.000000000*"j"$(d>=r 0)&d<r 1}

/ The session a time belongs to: the first calendar settlement at or after it.
/ cal is the sorted list of settlement dates; times past the last one get a null.
sessionof:{[cal;t] cal (settletime cal) binr t}

/ Last close in each k bucket, the bucket labelled by its end, so a bar closing
/ exactly on a boundary closes that bucket.
sample:{[b;k]
  `sym`time xasc 0!select last close, sum volume by sym, time:k+k xbar time-1 from b}

/ Log returns between consecutive samples of the same contract. Nothing resets at
/ a session boundary: a session's first return starts from the previous session's
/ last sample.
returns:{[s]
  update r:?[gapmax>=time-prev time;log[close]-log prev close;0n] by sym from s}

/ Realised variance, bipower variation and counts per contract and session.
/ bv uses only adjacent returns within the session.
measures:{[s;cal]
  s:update session:sessionof[cal;time] from returns s;
  0!select n:count r, rv:sum r*r, bv:(pi%2)*sum abs[r]*abs prev r, last_sample:last time
    by sym, session from s where not null r, not null session}

/ The daily table written by daily_rv.q: five-minute and one-minute measures side
/ by side, plus the contract's root, first and last bar and volume per session.
daily:{[b;cal]
  b:update session:sessionof[cal;time] from b;
  info:select root:first root, first_bar:first time, last_bar:last time, volume:sum volume
    by sym, session from b where not null session;
  m5:`sym`session xkey select sym, session, n5:n, rv5:rv, bv5:bv from measures[sample[b;k5];cal];
  m1:`sym`session xkey select sym, session, n1:n, rv1:rv from measures[sample[b;k1];cal];
  0!(info lj m5) lj m1}

/ Daily measures summed over (t, t+H] calendar days of each option's own
/ contract, by window join. d is the daily table; p has row_id, date, sym, tenor.
/ Sessions with fewer than minn 5-minute returns (thin back months) are left
/ out; rvol5 and rvol1 are annualised as in step 10, sqrt(252 * sum / sessions).
forward:{[d;p;minn]
  r:update `p#sym from `sym`session xasc select sym, session, rv5, bv5, rv1, n5, one:1 from d where not null rv5, n5>=minn;
  w:(p[`date]+1;p[`date]+p`tenor);
  f:wj1[w;`sym`session;select sym, session:date, row_id from p;(r;(sum;`rv5);(sum;`bv5);(sum;`rv1);(sum;`n5);(sum;`one))];
  select row_id, n_sessions:0^one, rv5_sum:0^rv5, bv5_sum:0^bv5, rv1_sum:0^rv1, n5_sum:0^n5,
    rvol5:sqrt 252*rv5%one, rvol1:sqrt 252*rv1%one from f}

\d .
