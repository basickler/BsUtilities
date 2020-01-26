# BS Utilities

Just some code I wanted to share here.

## REPORT_COMBINER.py
Extremely useful script that can intelligently combine CSV files with headers. 
Does some oddball math to try and keep the columns in the same order. Fills unavailable values with NULL.

To use
```shell script
./REPORT_COMBINER --delimter "," FILE1.csv FILE2.csv > COMBINED_FILE.csv
```

It'll assume that the file is tab delimited by default. 
Add -f to append file names as the first columns.
Run with --help to get a full listing of options.