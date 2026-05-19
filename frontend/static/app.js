const { createApp, ref, onMounted,watch ,defineComponent,nextTick ,reactive } = Vue;

// 子组件
const TreeNode = defineComponent({
  name: 'TreeNode',
  props: ['name'],
  setup(props, { expose }) {
    const isOpen = ref(false);
    const toggleOpen = () => {
      isOpen.value = !isOpen.value;
    };

    // 让父组件可以调用
    expose({
      toggleOpen,
      isOpen
    });

    return () => h('div', [
      h('span', props.name + (isOpen.value ? ' [Open]' : ' [Closed]'))
    ]);
  }
});

// 父组件
const App = {
  components: { TreeNode },
  setup() {
    const treeRef = ref(null);

    const openNode = () => {
      if (treeRef.value) {
        treeRef.value.toggleOpen();
        console.log('isOpen:', treeRef.value.isOpen);
      }
    };

    return () => h('div', [
      h(TreeNode, { ref: treeRef, name: 'Node 1' }),
      h('button', { onClick: openNode }, 'Toggle Open from Parent')
    ]);
  }
};

createApp(App).mount('#app');