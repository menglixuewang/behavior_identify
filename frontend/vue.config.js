const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  lintOnSave: false,

  devServer: {
    port: 8080,
    host: 'localhost',
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        ws: true,
        logLevel: 'debug',
        onProxyReq: function(proxyReq, req, res) {
          console.log('🔄 代理API请求:', req.url);
        },
        onError: function(err, req, res) {
          console.log('❌ API代理错误:', err.message);
        }
      },
      '/video_feed': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        ws: false,
        logLevel: 'debug',
        onProxyReq: function(proxyReq, req, res) {
          console.log('🎥 代理视频流请求:', req.url);
        },
        onError: function(err, req, res) {
          console.log('❌ 视频流代理错误:', err.message);
        }
      },
      '/socket.io': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        ws: true,
        logLevel: 'debug'
      }
    }
  },

  configureWebpack: {
    resolve: {
      fallback: {
        "path": false,
        "os": false,
        "crypto": false
      }
    }
  },

  // 添加Vue特性标志配置
  chainWebpack: config => {
    config.plugin('define').tap(definitions => {
      Object.assign(definitions[0]['process.env'], {
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
      })
      return definitions
    })
  }
})
