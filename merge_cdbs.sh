#!/bin/bash
echo "begin;"
for i in *.cdb;do
[[ "$i" == "cards.cdb" ]] && continue
echo "attach '${i}' as new;"
echo "insert or replace into datas select * from new.datas;"
echo "insert or replace into texts select * from new.texts;"
echo "detach new;"
done
echo "commit;"
