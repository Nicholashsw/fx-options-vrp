/ Command-line options and absolute paths for the scripts. Loading an HDB changes
/ the working directory, so every path is resolved before that happens.
/ .z.f is the script q was started with, so .cli.here is that script's folder.

.cli.args:.Q.opt .z.x;
.cli.opt:{[k] $[k in key .cli.args; " " sv .cli.args k; [-2"missing option -",string k; exit 1]]};
.cli.optd:{[k;d] $[k in key .cli.args; " " sv .cli.args k; d]};
.cli.abs:{[p] $["/"=first p; p; (first system "cd"),"/",p]};
.cli.here:{$[count d:-1_"/" vs string .z.f; "/" sv d; "."]}[];
.cli.done:{if[not `keep in key .cli.args; exit 0]};
