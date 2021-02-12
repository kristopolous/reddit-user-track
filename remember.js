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
        <video poster="tnail.php?url=data/${who}/${asset}" preload=none loop muted='' controls class=video muted="">
        <source src="data/${who}/${asset}">
        </video>
        `;
    } else {
      html = `<a target=_blank onclick="vote('${who}',0.1)" href=data/${who}/${asset}><img src="tnail.php?url=data/${who}/${asset}"></a>`;
    }
    content.push(html);
  }
  handler.classList.add('all');
  handler.innerHTML = content.join('');
}

// dir can also be amount
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

window.onload = function() {
  let cont = document.getElementById('content');
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
       ${last} ( ${days} ) <a href="https://reddit.com/u/${user}">profile</a>
     `;

     content.push([count, r]);
     cont.removeChild(r);
  });
  content.sort((b,a) => a[0] - b[0]).forEach(r => {
    cont.appendChild(r[1])
  });
}

