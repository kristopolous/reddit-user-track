#!/usr/bin/nodejs

const fs = require('fs');

let map = JSON.parse(fs.readFileSync('save.json'));
let list = [];

for (var k in map) {
  list.push([k, map[k]]);
}
list.sort((a,b) => a[1] - b[1]).forEach(row => {
  console.log(row[1], row[0]);
});

