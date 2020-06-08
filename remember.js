function showall(who,el) {
  if(who in showall) {
    return;
  }
  var handler = el.parentNode.parentNode.querySelector('.inner');
  handler.innerHTML = '';
  let content = [];
  for(let asset of all[who]) {
    let html = '';
    console.log(asset);
    let ext = asset.split('.').pop();
    if(ext == 'mp4' || ext == 'gifv') {
      html = ` 
        <video class=video autoplay loop muted="" nocontrols>
        <source src=data/${who}/${asset}>
        </video>
        `;
    } else {
      html = `<img src=data/${who}/${asset}>`;
    }
    content.push(html);
  }
  handler.classList.add('all');
  handler.innerHTML = content.join('');
}

function vote(who, dir) {
  var record = JSON.parse(localStorage['ballot'] || '{}');
  if(who) {
    if(! (who in record) ) {
      record[who] = 0;
    }
    if(dir) {
      record[who] += dir;
    }
    localStorage['ballot'] = JSON.stringify(record);
    return record[who];
  }
  return record;
}

function show(p) {
  Array.from(p.querySelectorAll('img,source'))
    .filter(l => !l.src)
    .forEach( r => {
      r.src = r.dataset.src;
    });
  p.classList.add('show');
}

window.onload = function() {
  if (document.querySelectorAll('img,source').length < 400) {
    show(document.body);
  } else {
    document.querySelectorAll(".inner").forEach( r => {
      r.addEventListener('mouseenter', e => { show(e.target); })
      r.addEventListener('mouseleave', e => {
        Array.from(e.target.querySelectorAll('img,source'))
          .forEach( r => {
            if(r.dataset.src) {
              r.removeAttribute('src');
            }
          });
        e.target.classList.remove('show');
      })
    });
  }
  let content = [];
  document.querySelectorAll(".cont").forEach( r => {
     let 
       user = r.dataset.user,
       controls = r.querySelector('.user'), 
       count = vote(user);
     
     controls.innerHTML = `<a onclick=showall("${user}",this)>${user}</a>
       <b>${count}</b>
       <a onclick=vote("${user}",1)>&#9650;</a> - 
       <a onclick=vote("${user}",-1)>&#9660;</a> 
     `;

     content.push([count, r]);
     document.body.removeChild(r);
  });
  content.sort((b,a) => a[0] - b[0]).forEach(r => {
    document.body.appendChild(r[1])
  });
}
