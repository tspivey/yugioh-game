# Yugioh MUD

This is a text-based Yu-Gi-Oh [MUD](https://en.wikipedia.org/wiki/MUD) server, written in Python.
It allows multiple players to duel with Yu-Gi-Oh cards.

## Usage

### Running via Docker

We include a Dockerfile which will build a working MUD server for you. We don't push the containers to any registry yet though, so you'll have to clone this repository and build a container yourself. Navigate into the directory of this repository:

    docker build . -t yugioh
    docker run --rm -p 4000:4000/tcp -d --name=yugioh yugioh
    
You can also feed your game database in as a volume, which works under Windows as well as Linux.

    docker run --rm -p 4000:4000/tcp -d -v /path/to/game.db:/usr/src/app/game.db --name=yugioh yugioh

### Building from scratch

#### Install dependencies
Lua is needed for ygopro-core. To make sure a matching lua version is used, we will compile it on our own:

    wget https://www.lua.org/ftp/lua-5.3.5.tar.gz
    tar xf lua-5.3.5.tar.gz
    cd lua-5.3.5
    make linux CC=g++ CFLAGS='-O2 -fPIC'

Install Python dependencies:
    pip3 install -r requirements.txt

#### Building

The following commands will assume your custom lua build to be found in your home directory. Adapt the corresponding lines to your liking.

ygopro-core and ygopro-scripts must be placed one level up from here.

```
git clone https://github.com/Fluorohydride/ygopro-core
git clone https://github.com/Fluorohydride/ygopro-scripts
cd ygopro-core
patch -p0 < ../yugioh-game/etc/ygopro-core.patch
g++ -shared -fPIC -o ../yugioh-game/libygo.so *.cpp -I$HOME/lua-5.3.5/src -L$HOME/lua-5.3.5/src -llua -std=c++14
cd ../yugioh-game
python3 duel_build.py
ln -s ../ygopro-scripts script
```

#### Compile language catalogues
This game supports multiple languages (english, spanish, german and french right now).
To compile the language catalogues, run the following:
```
./compile.sh de
./compile.sh es
./compile.sh fr
```

To update the plain text files into human-readable format, run the following:
```
./update.sh de
./update.sh es
./update.sh fr
```
The generated files in locale/<language code>/LC_MESSAGES/game.po can be given to translators afterwards.

#### Card databases

You'll need to grab the card databases for all languages you'd like to enable on your server. You'll at least need the database for the primary language (mostly english).
Those can be found on various sources on the net, but it would be the best to checkout the official ygopro2 discord server, download and update the full package and use the files which can be found inside the cdb folder.

ATTENTION: the most up-to-date english databases can be found directly within the cdb folder (no sub-folder), so just grab all *.cdb files and copy them over into the locale/en/ folder to get the server up and running.

The YGOPRO2 discord server can be found [here](https://discordapp.com/invite/8S5KcMJ).

#### Running
```
python3 ygo.py
```
The server will start on port 4000.

#### Upgrading

##### ygopro-scripts

When upgrading ygopro-scripts, always upgrade ygopro-core with it to prevent crashes. To do so, git pull the repositories cloned earlier and execute the build commands from above again.

##### This game

We might change several basic things from time to time, like adding additional c-level helper functions or modify the database layout, so don't forget to run the following commands whenever pulling a major upgrade:
```
python3 duel_build.py
alembic upgrade head
```
Always remember that, even though we try to prevent it, upgrading the database might fail and leave your database in a broken state, so always back it up before proceeding.
