## Install dependencies
Lua is needed for ygopro-core. On Ubuntu:
    apt-get install lua5.2-dev

Install Python dependencies:
    pip3 install -r requirements.txt
## Building
ygopro-core and ygopro-scripts must be placed one level up from here.
```
git clone https://github.com/Fluorohydride/ygopro-core
git clone https://github.com/Fluorohydride/ygopro-scripts
cd ygopro-core
patch -p0 < ../yugioh-game/etc/ygopro-core.patch
g++ -shared -fPIC -o ../yugioh-game/libygo.so *.cpp -I/usr/include/lua5.2 -llua5.2 -std=c++11
cd ../yugioh-game
python3 duel_build.py
ln -s ../ygopro-scripts script
mkdir expansions
ln -s ../ygopro-scripts expansions/script
```

## Running
Put a deck in deck.ydk.
The file format is just card codes separated by newlines.
```
python3 server.py
```
The server will start on port 4000.
