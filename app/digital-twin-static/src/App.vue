<template>
  <v-app id="inspire">
    <v-navigation-drawer
      v-model="drawer"
      fixed
      app
      >
      <v-list dense>

        <v-list-tile to="/">
          <v-list-tile-action>
            <v-icon>home</v-icon>
          </v-list-tile-action>
          <v-list-tile-content>
            <v-list-tile-title>Home</v-list-tile-title>
          </v-list-tile-content>
        </v-list-tile>
        <v-list-tile to="/equipment">
          <v-list-tile-action>
            <v-icon>directions_boat</v-icon>
          </v-list-tile-action>
          <v-list-tile-content>
            <v-list-tile-title>Equipment</v-list-tile-title>
          </v-list-tile-content>
        </v-list-tile>
        <v-list-tile to="/project">
          <v-list-tile-action>
            <v-icon>work</v-icon>
          </v-list-tile-action>
          <v-list-tile-content>
            <v-list-tile-title>Projects</v-list-tile-title>
          </v-list-tile-content>
        </v-list-tile>
      </v-list>
    </v-navigation-drawer>
    <v-toolbar color="indigo" dark fixed app>
      <v-toolbar-side-icon @click.stop="drawer = !drawer"></v-toolbar-side-icon>
      <v-toolbar-title>Application</v-toolbar-title>
    </v-toolbar>
    <v-content>
      <v-container fluid fill-height>
        <v-layout
          justify-center
          align-center
          >
          <router-view/>

        </v-layout>
      </v-container>
    </v-content>
    <v-footer color="indigo" app>
      <span class="white--text">&copy; 2017</span>
    </v-footer>
  </v-app>
</template>

<script>
export default {
  data: () => ({
    drawer: false
  }),

  props: {
    source: String
  }
}
</script>

<style lang="scss"></style>
