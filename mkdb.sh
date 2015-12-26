#!/bin/sh

FN=book.sqlite3

if [ -f $FN ]
then
    echo Database $FN already exists.  Will not overwrite
    exit 1
fi
sqlite3 $FN < book.schema
