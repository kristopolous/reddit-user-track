#!/usr/bin/nodejs

const fs = require('fs');
const glob = require('glob');
let scoreMap = {};

glob('data/*/subreddit.txt', {}, (err, fileList) => {
  fileList.forEach(path => {
    let subMap = JSON.parse(fs.readFileSync(path));
    for(let key in subMap) {
      if(! (key in scoreMap) ) {
        scoreMap[key] = 0;
      }
      scoreMap[key] += subMap[key];
    }
  });

  Object.keys(scoreMap)
    .map(key => [key, scoreMap[key]])
    .sort((a,b) => a[1] - b[1]).forEach(row => {
      if(row[0].slice(0,2) !== 'u_') {
        console.log(row[1], row[0]);
      }
    });
});

