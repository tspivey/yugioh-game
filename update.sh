#!/bin/bash
pybabel extract -k __ . -o game.pot &&
pybabel update --no-wrap -N -i game.pot -l $1 -D game -d locale
