#
# Create docker container anketa 
# run script in tools dir.
# If run in other location change SRC var

SRC='../'
NAME_IMAGE='dimania/anketa'

# copy files for container to tmp

temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

cp ${SRC}/anketa.py $temp_dir
cp ${SRC}/dbmodule.py $temp_dir
cp ${SRC}/settings.py $temp_dir
cp ${SRC}/config.py $temp_dir
cp ${SRC}/README.MD $temp_dir
cp ${SRC}/LICENSE $temp_dir
cp ${SRC}/requirements.txt $temp_dir
#cp -R ${SRC}/locales $temp_dir
cp -R ${SRC}/reports $temp_dir
cp -R ${SRC}/questionfiles $temp_dir
mkdir $temp_dir/logs
mkdir $temp_dir/session
mkdir $temp_dir/data


docker build --no-cache --file ${SRC}/tools/Dockerfile -t ${NAME_IMAGE} $temp_dir

docker push ${NAME_IMAGE}

rm -rf "$temp_dir"
