<?php

$path = $_GET['path'];
unlink($_SERVER['DOCUMENT_ROOT'] . '/' . parse_url($path, PHP_URL_PATH));
