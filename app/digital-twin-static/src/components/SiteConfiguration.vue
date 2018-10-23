<template>
  <v-card>
    <div class="jsoneditor"></div>
  </v-card>

</template>

<script>
// @ is an alias to /src

import JSONEditor from 'jsoneditor'

import 'jsoneditor/dist/jsoneditor.min.css'

export default {
  name: 'site-configuration',
  props: {
    'site': Object
  },
  data () {
    return {
      editor: null
    }
  },
  mounted () {
    let options = {}
    let container = this.$el.getElementsByClassName('jsoneditor')[0]
    let editor = new JSONEditor(container, options)
    this.editor = editor
    this.editor.set(
      this.site
    )
  },
  watch: {
    'site': {
      handler: function (newValue, oldValue) {
        console.log('site', newValue)
        if (this.editor) {
          this.editor.set(
            this.site
          )
          this.editor.expandAll()
        }
      },
      deep: true

    }
  },
  components: {
  }
}
</script>
