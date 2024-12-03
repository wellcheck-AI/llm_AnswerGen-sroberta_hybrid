apt-get update
apt-get install git build-essential default-jdk autoconf automake libtool pkg-config gcc g++ curl gettext -y
rm -rf /var/lib/apt/lists/*
git clone https://github.com/Daewoong-wellcheckAI/mecab.git
cd mecab
tar zxfv mecab-0.996-ko-0.9.2.tar.gz
tar -zxvf mecab-ko-dic-2.1.1-20180720.tar.gz
rm *.gz
cd mecab-ko-dic-2.1.1-20180720
ldconfig
ldconfig -p | grep /usr/local/lib
cd ..

echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
ldconfig

cd mecab-0.996-ko-0.9.2
./configure
make
make check
make install
cd ..

cd mecab-ko-dic-2.1.1-20180720
./autogen.sh
./configure
make
make install
cd ..

pip install mecab-python3