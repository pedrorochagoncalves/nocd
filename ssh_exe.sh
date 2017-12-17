#!/bin/sh
ID_RSA=/te/.ssh/id_rsa
exec /usr/bin/ssh -o StrictHostKeyChecking=no -i $ID_RSA "$@"
