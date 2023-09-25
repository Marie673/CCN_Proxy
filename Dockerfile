FROM ubuntu:22.04
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN mkdir -p /cefore
WORKDIR /cefore

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y python3.10
RUN apt-get install -y python3.10-venv

RUN apt-get install -y git build-essential libssl-dev libtool
RUN apt-get install -y emacs
RUN apt-get install -y iputils-ping net-tools ifstat
RUN apt-get install -y cmake python3-pip
RUN apt-get install -y xserver-xorg x11-apps
RUN pip3 install --upgrade pip
RUN pip3 install setuptools click numpy
RUN pip3 install --upgrade  build
RUN pip3 install rich pytest pytest-sugar
RUN apt-get remove -y python3-blinker

RUN apt-get install -y wget
RUN apt-get install -y perl
RUN apt-get install -y autoconf
RUN apt-get install -y automake

RUN apt-get -y clean

WORKDIR /cefore
RUN git clone https://github.com/cefore/cefore.git
RUN git clone https://github.com/cefore/cefpyco

WORKDIR /cefore/cefore
RUN autoconf
RUN aclocal
RUN automake --add-missing
RUN ./configure --enable-cache --enable-csmgr
RUN make
RUN make install
RUN make clean
RUN ldconfig

WORKDIR /cefore/cefpyco
RUN cmake .
RUN make install

COPY ./ /cefore/proxy
WORKDIR /cefore/proxy
RUN pip3 install -r requirements.txt
