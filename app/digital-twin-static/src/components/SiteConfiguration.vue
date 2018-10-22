<template>
  <v-container grid-list-md >
    <v-layout row wrap >
      <v-flex xs4 v-for="feature in site.features.features" :key="feature.id">
        <v-card>
          {{ feature }}
        </v-card>
      </v-flex>
    </v-layout>
  </v-container>

</template>

<script>
// @ is an alias to /src

export default {
  name: 'site-configuration',
  props: {
    'site': Object
  },
  data () {
    return {}
  },
  components: {
  }
}
</script>
