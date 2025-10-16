# ========= Config =========
IMAGE      ?= mongo:latest
CONTAINER  ?= planerProj2
PORT       ?= 27017
HOST       ?= localhost

MONGO_USER ?= admin
MONGO_PASS ?= secret
MONGO_DB   ?= mydatabase

VOLUME     ?= mongo_data
DATA_DIR   ?=

NET             ?= mongo_net


EXP_IMAGE       ?= mongo-express:latest
EXP_CONTAINER   ?= mongo-express
EXP_PORT        ?= 8081

EXP_BASIC_USER  ?= admin
EXP_BASIC_PASS  ?= admin

DATE := $(shell date +%Y%m%d_%H%M%S)

# Вычисляем, чем монтировать хранилище
ifeq ($(strip $(DATA_DIR)),)
  STORAGE=-v $(VOLUME):/data/db
else
  STORAGE=-v $(DATA_DIR):/data/db
endif

# ========= Phony =========
.PHONY: help up run start stop restart ps logs rm purge shell mongosh wait ping url \
        pull volume net connect_net backups_dir dump restore seed wipe clean prune status \
        express_up express_down express_restart express_logs express_rm express_status express_url

help:
	@echo "MongoDB via plain Docker:"
	@echo "  make up              - запустить MongoDB (создаст контейнер, если его нет)"
	@echo "  make start/stop      - запустить/остановить контейнер MongoDB"
	@echo "  make restart         - перезапустить MongoDB"
	@echo "  make ps/status       - статус контейнера MongoDB"
	@echo "  make logs            - логи MongoDB (follow)"
	@echo "  make mongosh         - открыть mongosh с авторизацией"
	@echo "  make wait            - дождаться готовности порта $(PORT)"
	@echo "  make ping            - db.runCommand({ ping: 1 })"
	@echo "  make url             - показать URI подключения"
	@echo "  make dump            - бэкап в ./backups/$(MONGO_DB)_<stamp>.archive"
	@echo "  make restore ARCHIVE=backups/....archive"
	@echo "  make wipe            - dropDatabase($(MONGO_DB))"
	@echo "  make rm/purge        - удалить контейнер (purge: + удалить volume/данные)"
	@echo "  make clean/prune     - удалить volume (если named) / почистить docker"
	@echo ""
	@echo "Mongo-Express:"
	@echo "  make express_up      - запустить mongo-express (http://localhost:$(EXP_PORT))"
	@echo "  make express_down    - остановить mongo-express"
	@echo "  make express_restart - перезапустить mongo-express"
	@echo "  make express_logs    - логи mongo-express"
	@echo "  make express_status  - статус mongo-express"
	@echo "  make express_rm      - удалить контейнер mongo-express"
	@echo "  make express_url     - показать URL UI"

# ========= Lifecycle (MongoDB) =========
up: pull net
	@if docker ps -a --format '{{.Names}}' | grep -wq $(CONTAINER); then \
	  echo "Контейнер MongoDB уже существует. Запускаю..."; \
	  docker start $(CONTAINER) >/dev/null || true; \
	  $(MAKE) connect_net >/dev/null; \
	else \
	  $(MAKE) run; \
	fi
	@$(MAKE) wait

run: volume net
	@echo "Стартую MongoDB ($(IMAGE)) на порту $(PORT) ..."
	@docker run -d --name $(CONTAINER) \
	  --network $(NET) \
	  -p $(PORT):27017 \
	  -e MONGO_INITDB_ROOT_USERNAME=$(MONGO_USER) \
	  -e MONGO_INITDB_ROOT_PASSWORD=$(MONGO_PASS) \
	  $(STORAGE) \
	  $(IMAGE) >/dev/null
	@echo "Готово."

start:
	@docker start $(CONTAINER)

stop:
	@docker stop $(CONTAINER)

restart: stop start

ps status:
	@docker ps -a --filter name=$(CONTAINER)

logs:
	@docker logs -f $(CONTAINER)

rm:
	- docker rm -f $(CONTAINER) 2>/dev/null || true

purge: rm clean

shell:
	@docker exec -it $(CONTAINER) bash

mongosh:
	@docker exec -it $(CONTAINER) mongosh -u $(MONGO_USER) -p $(MONGO_PASS) --authenticationDatabase admin

wait:
	@echo "Ожидаю доступность $(HOST):$(PORT) ..."
	@until nc -z $(HOST) $(PORT) >/dev/null 2>&1 ; do sleep 0.5 ; done
	@echo "Порт открыт."

ping:
	@docker exec -it $(CONTAINER) mongosh -u $(MONGO_USER) -p $(MONGO_PASS) --authenticationDatabase admin --eval 'db.runCommand({ ping: 1 })'

url:
	@echo "mongodb://$(MONGO_USER):$(MONGO_PASS)@$(HOST):$(PORT)/$(MONGO_DB)"

pull:
	@docker pull $(IMAGE) >/dev/null

# ========= Network / Storage helpers =========
net:
	@docker network inspect $(NET) >/dev/null 2>&1 || docker network create $(NET) >/dev/null

connect_net:
	@docker network inspect $(NET) >/dev/null 2>&1 || docker network create $(NET) >/dev/null
	@docker network connect $(NET) $(CONTAINER) 2>/dev/null || true

volume:
ifeq ($(strip $(DATA_DIR)),)
	@docker volume inspect $(VOLUME) >/dev/null 2>&1 || docker volume create $(VOLUME) >/dev/null
else
	@mkdir -p $(DATA_DIR)
endif

clean:
ifeq ($(strip $(DATA_DIR)),)
	- docker volume rm $(VOLUME) 2>/dev/null || true
else
	@echo "DATA_DIR задан ( $(DATA_DIR) ) — ничего не удаляю."
endif

backups_dir:
	@mkdir -p backups

dump: backups_dir
	@echo "Бэкап БД '$(MONGO_DB)' в backups/$(MONGO_DB)_$(DATE).archive ..."
	@docker exec $(CONTAINER) sh -c "\
		mongodump -u $(MONGO_USER) -p $(MONGO_PASS) --authenticationDatabase admin \
		--db '$(MONGO_DB)' --archive" \
	> backups/$(MONGO_DB)_$(DATE).archive
	@echo "OK: backups/$(MONGO_DB)_$(DATE).archive"

restore:
ifndef ARCHIVE
	$(error Укажи файл: make restore ARCHIVE=backups/file.archive)
endif
	@echo "Восстанавливаю БД '$(MONGO_DB)' из $(ARCHIVE) ..."
	@docker exec -i $(CONTAINER) sh -c "\
		mongorestore -u $(MONGO_USER) -p $(MONGO_PASS) --authenticationDatabase admin \
		--nsInclude='$(MONGO_DB).*' --archive" < $(ARCHIVE)
	@echo "Готово."

# Полностью очистить БД (dropDatabase)
wipe:
	@echo "Drop database $(MONGO_DB) ..."
	@docker exec -i $(CONTAINER) mongosh -u $(MONGO_USER) -p $(MONGO_PASS) --authenticationDatabase admin --eval "db.getSiblingDB('$(MONGO_DB)').dropDatabase()"
	@echo "Готово."

prune:
	@docker system prune -f
	@docker volume prune -f

# ========= Mongo-Express =========
express_up: net connect_net
	@echo "Запускаю mongo-express ($(EXP_IMAGE)) на порту $(EXP_PORT) ..."
	@if docker ps -a --format '{{.Names}}' | grep -wq $(EXP_CONTAINER); then \
	  echo "Контейнер mongo-express уже существует. Запускаю..."; \
	  docker start $(EXP_CONTAINER) >/dev/null || true; \
	else \
	  docker run -d --name $(EXP_CONTAINER) \
	    --network $(NET) \
	    -p $(EXP_PORT):8081 \
	    -e ME_CONFIG_MONGODB_ADMINUSERNAME=$(MONGO_USER) \
	    -e ME_CONFIG_MONGODB_ADMINPASSWORD=$(MONGO_PASS) \
	    -e ME_CONFIG_MONGODB_SERVER=$(CONTAINER) \
	    -e ME_CONFIG_BASICAUTH_USERNAME=$(EXP_BASIC_USER) \
	    -e ME_CONFIG_BASICAUTH_PASSWORD=$(EXP_BASIC_PASS) \
	    $(EXP_IMAGE) >/dev/null ; \
	fi
	@echo "mongo-express доступен: http://localhost:$(EXP_PORT)"
	@echo "UI basic auth: $(EXP_BASIC_USER) / $(EXP_BASIC_PASS)"

express_down:
	- docker stop $(EXP_CONTAINER) 2>/dev/null || true

express_restart: express_down express_up

express_logs:
	@docker logs -f $(EXP_CONTAINER)

express_status:
	@docker ps -a --filter name=$(EXP_CONTAINER)

express_rm:
	- docker rm -f $(EXP_CONTAINER) 2>/dev/null || true

express_url:
	@echo "http://localhost:$(EXP_PORT)"
