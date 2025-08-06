# Dev guide

## Create a migration file

```sh
docker-compose run --entrypoint /bin/bash latex -c "goose -s create <migration_name> sql"
sudo 
make set-permissions-migrations
```
