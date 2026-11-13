/ Running realised variance, one bar at a time, for the real-time subscriber.

/ The same measures as .rv.measures on the five-minute grid, computed
/ incrementally: a bucket becomes a sample when the contract's first bar of a
/ later bucket arrives, and that sample's return is added to the session the
/ bucket ends in. After .live.flush[] has closed the open buckets, .live.acc
/ equals .rv.measures over the same bars (tests/test_rv.q checks it).

\d .live

cal:`date$();
st:([sym:`symbol$()] bucket:`timestamp$(); last_close:`float$(); prev_bucket:`timestamp$();
    prev_close:`float$(); prev_r:`float$(); prev_session:`date$());
acc:([sym:`symbol$(); session:`date$()] n:`long$(); rv:`float$(); bv:`float$());

/ Turn the contract's current bucket into a sample.
close:{[s]
  x:st s;
  if[not null x`prev_close;
    if[.rv.gapmax>=x[`bucket]-x`prev_bucket;
      r:log[x`last_close]-log x`prev_close;
      ses:.rv.sessionof[cal;x`bucket];
      if[not null ses;
        bv:$[ses=x`prev_session; (.rv.pi%2)*abs[r]*abs x`prev_r; 0f];
        o:acc (s;ses);
        `.live.acc upsert (s;ses;1+0^o`n;(0^o`rv)+r*r;(0^o`bv)+bv);
        `.live.st upsert (s;x`bucket;x`last_close;x`prev_bucket;x`prev_close;r;ses);
        x:st s]]];
  `.live.st upsert (s;x`bucket;x`last_close;x`bucket;x`last_close;x`prev_r;x`prev_session);
  }

onbar:{[s;t;c]
  b:.rv.k5+.rv.k5 xbar t-1;
  x:st s;
  $[null x`bucket; `.live.st upsert (s;b;c;0Np;0n;0n;0Nd);
    b>x`bucket; [close s; `.live.st upsert (s;b;c),value[st s] 2 3 4 5];
    `.live.st upsert (s;x`bucket;c),value[x] 2 3 4 5];
  }

onbars:{[x] onbar'[x`sym;x`time;x`close];}

flush:{close each exec sym from st;}

/ Annualised running volatility per contract for the sessions seen so far.
.live.view:{select sym, session, n, rvol:sqrt 252*rv, bvol:sqrt 252*bv from acc}

\d .
