rm -Rf shasums
mkdir shasums

user=root
host=mynas
basedir=/mnt

getIndex() {
  path=$1
  scp $user@$host:$basedir/$1/folder-index.txt shasums/$1.txt
  scp $user@$host:$basedir/$1/nohup.out shasums/$1.err
}

getIndex documents
getIndex photos
