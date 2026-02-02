const levels = ['debug', 'info', 'warn', 'error'];

function createLogger(level = 'info') {
  const currentIndex = levels.indexOf(level);
  const shouldLog = (lvl) => levels.indexOf(lvl) >= currentIndex;

  return {
    debug: (...args) => {
      if (shouldLog('debug')) console.debug('[debug]', ...args);
    },
    info: (...args) => {
      if (shouldLog('info')) console.info('[info]', ...args);
    },
    warn: (...args) => {
      if (shouldLog('warn')) console.warn('[warn]', ...args);
    },
    error: (...args) => {
      if (shouldLog('error')) console.error('[error]', ...args);
    },
  };
}

module.exports = {
  createLogger,
};
