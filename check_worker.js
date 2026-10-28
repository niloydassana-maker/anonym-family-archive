const https = require('https');

https.get('https://banana-newman-discussed-flag.trycloudflare.com/say?token=GOLD24&text=JOB_QUERY%20WORKER_ALIVE', (res) => {
  let d = '';
  res.on('data', c => d += c);
  res.on('end', () => {
    const lines = d.split('},{');
    const alive = lines.filter(l => l.includes('WORKER_ALIVE'));
    console.log('Found', alive.length, 'WORKER_ALIVE');
    alive.slice(-3).forEach(a => console.log(a.slice(-200)));
  });
}).on('error', e => console.error(e.message));