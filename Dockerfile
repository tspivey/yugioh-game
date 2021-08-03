FROM python:3.7 AS BUILD_IMAGE

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY etc/ ./etc/
COPY duel_build.py ./
COPY locale/ ./locale/
COPY compile.sh ./

RUN mkdir ./pip && \
    pip install --prefix "/usr/src/app/pip" -r requirements.txt && \
    pip install cffi babel && \
    git clone https://github.com/Fluorohydride/ygopro-core core && \
    git clone https://github.com/Fluorohydride/ygopro-scripts script && \
    wget https://www.lua.org/ftp/lua-5.3.5.tar.gz && \
    apt-get update && \
    apt-get install -y build-essential gettext

RUN tar xf lua-5.3.5.tar.gz && \
    cd lua-5.3.5 && \
    make linux CC=g++ CFLAGS='-O2 -fPIC' && \
    cd ../core && \
    patch -p0 < ../etc/ygopro-core.patch && \
    g++ -shared -fPIC -o ../libygo.so *.cpp -I../lua-5.3.5/src -L../lua-5.3.5/src -llua -std=c++14 && \
    cd .. && \
    python duel_build.py && \
    ./compile.sh de && \
    ./compile.sh fr && \
    ./compile.sh es && \
    ./compile.sh ja && \
    ./compile.sh pt

FROM python:3.7.11-slim-buster

WORKDIR /usr/src/app

COPY ygo/ ./ygo/
COPY ygo.py ./
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY lflist.conf ./
COPY --from=BUILD_IMAGE /usr/src/app/*.so ./
COPY --from=BUILD_IMAGE /usr/src/app/script/ ./script/
COPY --from=BUILD_IMAGE /usr/src/app/pip /usr/local
COPY --from=BUILD_IMAGE /usr/src/app/locale/ ./locale/

EXPOSE 4000

CMD ["python", "-u", "ygo.py"]
