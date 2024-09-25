var _ban = false;
function showall(who,el) {
  if(who in showall) {
    return;
  }
  var handler = el.parentNode.parentNode.querySelector('.inner');
  handler.innerHTML = '';
  let content = [];
  for(let asset of all[who]) {
    let html = '';
    asset = encodeURIComponent(asset);
    let ext = asset.split('.').pop();
    if(ext == 'mp4' || ext == 'gifv') {
      html = ` 
        <video onclick=mayberemove(this) poster="tnail.php?url=data/${who}/${asset}" preload=none loop muted='' controls class=video muted="">
        <source src="data/${who}/${asset}">
        </video>
        `;
    } else if(ext == 'gif') {
      html = `<a target=_blank onclick="vote('${who}',0.1,this)" data-href=data/${who}/${asset}><img src="data/${who}/${asset}"></a>`;
    } else {
      html = `<a target=_blank onclick="vote('${who}',0.1,this)" data-href=data/${who}/${asset}><img src="tnail.php?url=data/${who}/${asset}"></a>`;
    }
    content.push(html);
  }
  handler.classList.add('all');
  handler.innerHTML = content.join('');
}

function mayberemove(what) {
  if (_ban) {
    what.style.display = 'none';
    fetch(`remove.php?path=${what.children.item(0).src}`);
    return;
  }
}


// dir can also be amount
function vote(who, dir, el) {
  if (_ban) {
    el.style.display = 'none';
    fetch(`remove.php?path=${el.dataset.href}`);
    // we actually continue with our logic but go
    // the opposite direction since we are removing
    // a thumbnail
    dir *= -0.5;
  }
  else if(el && el.dataset.href){
    window.open(el.dataset.href);
  }
  if (dir) {
    if(!(who in db)) {
      db[who] = 0;
    }
    db[who] = (parseFloat(db[who], 10) || 0) + dir;
    fetch(`vote.php?who=${who}&what=${db[who]}`);
  } 
  if(dir != 0.1 && el) {
    el.parentNode.getElementsByTagName('b')[0].innerHTML = db[who];
  }

  return db[who] || 0;
}

function toggle (el) {
  el.classList.toggle('active');
  document.body.classList.toggle('active');
  _ban = el.classList.contains('active')
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
     
     controls.innerHTML = `
       <b>${parseFloat(count).toFixed(2)}</b>
       <a onclick=showall("${user}",this)>${user}</a>`
       + ( 
           window.autoexpand ? '' : 
         `<a onclick=vote("${user}",1,this)>&#9650;</a> - 
          <a onclick=vote("${user}",-1,this)>&#9660;</a> `
       ) + `${last} ( ${days} ) <a class='profile-link' href="https://reddit.com/u/${user}">profile</a>
       <a class='profile-link' target=_blank href="comment.php?u=${user}">comments</a>
     `;

     if(window.autoexpand) {
       showall(user, controls.firstChild);
     }

     content.push([count, r]);
     cont.removeChild(r);
  });
  content.sort((b,a) => a[0] - b[0]).forEach(r => {
    cont.appendChild(r[1])
  });
}

