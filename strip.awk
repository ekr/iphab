				{ gsub(/\r/, ""); }
				{ gsub(/[ \t]+$/, ""); }
				{ pagelength++; }
/\[?[Pp]age [0-9ivx]+\]?[ \t\f]*$/	{
				    match($0, /[Pp]age [0-9ivx]+/);
				    num = substr($0, RSTART+5, RLENGTH-5);
				    pagelength = 0;
				}
/\f/				{ newpage=1;
				  pagelength=1;
				}
/\f$/				{
				    # a form feed followed by a \n does not contribute to the
				    # line count.  (But a \f followed by something else does.)
				    pagelength--;
				}
/\f/				{ next; }
/\[?[Pp]age [0-9ivx]+\]?[ \t\f]*$/		{ preindent = indent; next; }

/^ *Internet.Draft.+[12][0-9][0-9][0-9] *$/ && (FNR > 15)	{ newpage=1; next; }
/^ *INTERNET.DRAFT.+[12][0-9][0-9][0-9] *$/ && (FNR > 15)	{ newpage=1; next; }
/^ *Draft.+(  +)[12][0-9][0-9][0-9] *$/	    && (FNR > 15)	{ newpage=1; next; }
/^RFC[ -]?[0-9]+.*(  +).* [12][0-9][0-9][0-9]$/ && (FNR > 15)	{ newpage=1; next; }
/^draft-[-a-z0-9_.]+.*[0-9][0-9][0-9][0-9]$/ && (FNR > 15)	{ newpage=1; next; }
/(Jan|Feb|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|Sep|Oct|Nov|Dec) (19[89][0-9]|20[0-9][0-9]) *$/ && pagelength < 3  { newpage=1; next; }
newpage && $0 ~ /^ *draft-[-a-z0-9_.]+ *$/ { newpage=1; next; }

/^[ \t]+\[/			{ sentence=1; }
/[^ \t]/			{
				   indent = match($0, /[^ ]/);
				   if (indent < preindent) {
				      sentence = 1;
				   }
				   if (newpage) {
				      if (sentence) {
					 outline++; print "";
				      }
				   } else {
				      if (haveblank) {
					  outline++; print "";
				      }
				   }
				   haveblank=0;
				   sentence=0;
				   newpage=0;

				   line = $0;
				   sub(/^ *\t/, "        ", line);
				   thiscolumn = match(line, /[^ ]/);
				}
/[.:][ \t]*$/			{ sentence=1; }
/\(http:\/\/trustee\.ietf\.org\/license-info\)\./ { sentence=0; }
/^[ \t]*$/			{ haveblank=1; next; }
				{ outline++; print; }
