#!/bin/bash

set -ue -o pipefail

SCRIPT_DIR=$(cd $(dirname "${0}"); pwd)
HOSTNAME="localhost"
DATABASE_NAME="ARK"
DATABASE_DUMP_FILE="${SCRIPT_DIR}/${DATABASE_NAME}.sql"
DATABASE_DUMP_FILE_TMP="${DATABASE_DUMP_FILE}.tmp"
CONNECT_CONSECUTIVE_INSERT="${SCRIPT_DIR}/connect_consecutive_insert.py"
CONNECT_CONSECUTIVE_INSERT_URL="https://raw.githubusercontent.com/482F/misc/master/connect_consecutive_insert.py"
OPT="${1:-}"

function main(){
    mysqldump -h "${HOSTNAME}" -u root -p --skip-extended-insert --skip-dump-date "${DATABASE_NAME}" > "${DATABASE_DUMP_FILE_TMP}"

    if [ ! -e "${CONNECT_CONSECUTIVE_INSERT}" ]; then
        update
    fi

    if [ "${OPT}" = "--check" ]; then
        "${CONNECT_CONSECUTIVE_INSERT}" ${OPT} "${DATABASE_DUMP_FILE_TMP}"
    else
        "${CONNECT_CONSECUTIVE_INSERT}" "${DATABASE_DUMP_FILE_TMP}" > "${DATABASE_DUMP_FILE}"
    fi
    rm "${DATABASE_DUMP_FILE_TMP}"
}

function update(){
    curl "${CONNECT_CONSECUTIVE_INSERT_URL}" > "${CONNECT_CONSECUTIVE_INSERT}"
    chmod 744 "${CONNECT_CONSECUTIVE_INSERT}"
}

if [ "${OPT}" = "--update" ]; then
    update
else
    main
fi
