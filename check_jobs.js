const https = require('https');

https.get('https://banana-newman-discussed-flag.trycloudflare.com/say?token=GOLD24&text=JOB_QUERY%20JOB_', (res) => {
  let d = '';
  res.on('data', c => d += c);
  res.on('end', () => {
    const lines = d.split('},{');
    const jobs = lines.filter(l => l.includes('JOB_'));
    console.log('Found', jobs.length, 'JOB_ messages');
    jobs.slice(-10).forEach(a => console.log(a.slice(-300)));
  });
}).on('error', e => console.error(e.message));