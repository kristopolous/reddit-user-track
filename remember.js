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
        <source src="data/${who}/${asset}">
        </video>
        `;
    } else {
      html = `<img src="data/${who}/${asset}">`;
    }
    content.push(html);
  }
  handler.classList.add('all');
  handler.innerHTML = content.join('');
}

function vote(who, dir, el) {
  if (dir) {
    if(!(who in db)) {
      db[who] = 0;
    }
    db[who] = (parseInt(db[who], 10) || 0) + dir;
    fetch(`vote.php?who=${who}&what=${db[who]}`);
  } 
  if(el) {
    el.parentNode.getElementsByTagName('b')[0].innerHTML = db[who];
  }

  return db[who] || 0;
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
  let cont = document.getElementById('content');
  show(document.body);
  let content = [];
  document.querySelectorAll(".cont").forEach( r => {
     let 
       user = r.dataset.user,
       last = r.dataset.last,
       days = Math.floor(last / 24),
       controls = r.querySelector('.user'), 
       count = vote(user);
     
     controls.innerHTML = `<a onclick=showall("${user}",this)>${user}</a>
       <b>${count}</b>
       <a onclick=vote("${user}",1,this)>&#9650;</a> - 
       <a onclick=vote("${user}",-1,this)>&#9660;</a> 
       ${last} ( ${days} )
     `;

     content.push([count, r]);
     cont.removeChild(r);
  });
  content.sort((b,a) => a[0] - b[0]).forEach(r => {
    cont.appendChild(r[1])
  });
}

