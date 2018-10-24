<template>
  <div>
    <v-btn @click="run">Run</v-btn>
    <v-card>
      <v-card-title>
        <h2>Results</h2>
      </v-card-title>
      <v-card-text>
        <div class="jsoneditor"></div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
// @ is an alias to /src
import JSONEditor from 'jsoneditor'

import 'jsoneditor/dist/jsoneditor.min.css'

export default {
  name: 'activity-runner',
  props: {
    equipment: Array,
    site: Object
  },
  data () {
    return {
      results: {},
      editor: null
    }
  },
  mounted () {
    let options = {}
    let container = this.$el.getElementsByClassName('jsoneditor')[0]
    let editor = new JSONEditor(container, options)
    this.editor = editor
    this.editor.set(
      this.results
    )
  },
  methods: {
    run () {
      let obj = {
        origins: this.site.origins.features,
        destination: this.site.destination.features,
        equipment: this.equipment
      }
      fetch(
        'http://localhost:5000/simulate',
        {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(obj)
        }
      )
        .then(resp => {
          return resp.json()
        })
        .then(json => {
          this.results = json
        })
    }
  },
  watch: {
    'results': {
      handler: function (newValue, oldValue) {
        if (this.editor) {
          this.editor.set(
            this.results
          )
        }
      },
      deep: true

    }
  },
  components: {
  }
}
</script>
