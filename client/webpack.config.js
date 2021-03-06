const path = require('path')
const VueLoaderPlugin = require('vue-loader/lib/plugin');
const VuetifyLoaderPlugin = require('vuetify-loader/lib/plugin')
function resolve (dir) {
  return path.join(__dirname, '.', dir)
}

const BUNDLE_VERSION = '0.1.6'

module.exports = (env, argv) => {
  config = {
    entry: {
    'essay-utils' : './src/main.js'
    },
    output: {
      path: path.resolve(__dirname, '../docs'),
      publicPath: '/lib/',
      filename: argv.mode === 'production' ? `[name]-${BUNDLE_VERSION}.min.js` : "[name].js"
    },
    resolve: {
      extensions: ['.js', '.vue', '.json'],
      alias: {
        'vue$': 'vue/dist/vue.esm.js',
        '@': resolve('src'),
      }
    },
    module: {
      rules: [
        {
          test: /\.vue$/,
          loader: 'vue-loader'
        },
        // this will apply to both plain `.js` files
        // AND `<script>` blocks in `.vue` files
        {
          test: /\.js$/,
          loader: 'babel-loader'
        },
        // this will apply to both plain `.css` files
        // AND `<style>` blocks in `.vue` files
        {
          test: /\.css$/,
          use: [
            'vue-style-loader',
            'css-loader'
          ]
        },
        {
          test: /\.scss$/,
          use: [
            'vue-style-loader',
            'css-loader',
            'sass-loader'
          ]
        },
        {
          test: /\.sass$/,
          use: [
            'vue-style-loader',
            'css-loader',
            'sass-loader'
          ]
        },
        {
          test: /\.styl(us)?$/,
          use: [
            'vue-style-loader',
            'css-loader',
            'stylus-loader'
          ]
        },
        {
          test: /\.(jpe?g|png|gif|woff|woff2|eot|ttf|svg)(\?[a-z0-9=.]+)?$/,
          loader: 'url-loader?limit=100000' 
        }
      ]
    },
    plugins: [
      new VueLoaderPlugin(),
      new VuetifyLoaderPlugin()
    ]
  }
  return config
}
