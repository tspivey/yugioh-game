#!/bin/bash
pybabel extract -k __ ./ygo -o game.pot &&
pybabel update --no-wrap -N -i game.pot -l $1 -D game -d locale
