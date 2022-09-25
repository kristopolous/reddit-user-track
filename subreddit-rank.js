#!/usr/bin/nodejs

const fs = require('fs');

let subs = JSON.parse(fs.readFileSync('save.json'));

Object.keys(subs)
  .map(key => [key, subs[key]])
  .sort((a,b) => a[1] - b[1]).forEach(row => {
    if(row[0].slice(0,2) !== 'u_') {
      console.log(row[1], row[0]);
    }
  });

