docker-compose -f local.yml down &&
git pull &&
docker-compose -f local.yml build &&
docker-compose -f local.yml up -d

