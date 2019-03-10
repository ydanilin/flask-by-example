#!/bin/sh

# Author: Rainer Stropek
# Tested on Ubuntu 16.04 LTS on Windows 10 Pro

# On Ubuntu 16.04 LTS, you need to install (apt-get install) the following packages in order to run this script:
# * LaTeX (e.g. texlive texlive-lang-german texlive-latex-extra)
# * pandoc
# * librsvg2-bin

# Verify that argument has been given
if [ -z "$1" ]; then {
    echo "Error: Missing argument\n"
    echo "USAGE: $0 name-of-markdown-file"
    echo "Converts specified markdown file to pdf"
    exit 1
}
fi

# Check that file extension is .md
EXT=$1
EXT="${EXT##*.}"
if [ "$EXT" != "md" ]; then {
    echo "Error: Specified file name does not have the extension .md"
    exit 1
} fi

# Verify that file exists
if [ ! -f $1 ]; then {
    echo "Error: Specified file not found"
    exit 1
} fi

BASENAME=$(basename "$1" .md)

# Look for all SVG files in subdirectory having the same name
# as the markdown file to convert.
for f in ./$BASENAME/*.svg
do
    # Skip if not a file
    test -f "$f" || continue
    
    # Convert SVG file into PDF
    rsvg-convert $f -f pdf -o ./$BASENAME/$(basename "$f" .svg).pdf
done

## Convert markdown file into PDF
pandoc $1 -f markdown -t latex -o $BASENAME.pdf
