const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('appInfo', {
  name: 'AIwebApp',
  desktop: true,
})
