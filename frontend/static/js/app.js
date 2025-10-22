(function(){
  // Simple in-memory graph model
  const nodes = new vis.DataSet([])
  const edges = new vis.DataSet([])

  const container = document.getElementById('network')
  const data = { nodes, edges }
  const options = {
    edges: { color: '#9ca3ff' },
    nodes: { color: { background: '#7c3aed' }, font: { color: '#fff' } },
    interaction:{ hover:true, multiselect:true },
    physics: { stabilization: false }
  }
  const network = new vis.Network(container, data, options)

  // UI elements
  const addNodeBtn = document.getElementById('addNodeBtn')
  const exportBtn = document.getElementById('exportBtn')
  const importBtn = document.getElementById('importBtn')
  const importFile = document.getElementById('importFile')
  const fileInput = document.getElementById('fileInput')
  const uploadBtn = document.getElementById('uploadBtn')
  const docList = document.getElementById('docList')
  const chatLog = document.getElementById('chatLog')
  const queryInput = document.getElementById('queryInput')
  const sendQueryBtn = document.getElementById('sendQueryBtn')
  const clearChatBtn = document.getElementById('clearChatBtn')

  // Endpoint config for local backend
  const ENDPOINTS = {
    SEARCH: '/api/search_graph/'
  }

  // helpers
  function addNode(label){
    const id = Date.now() + Math.floor(Math.random()*1000)
    nodes.add({ id, label })
    return id
  }

  function addEdge(from,to){
    edges.add({ id: 'e'+from+'-'+to, from, to })
  }

  // toolbar
  addNodeBtn.addEventListener('click',()=>{
    const label = prompt('Node label') || 'New Node'
    addNode(label)
  })

  exportBtn.addEventListener('click',()=>{
    const payload = { nodes: nodes.get(), edges: edges.get() }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'graph.json'
    a.click(); URL.revokeObjectURL(url)
  })

  importBtn.addEventListener('click',()=> importFile.click())
  importFile.addEventListener('change', async (ev)=>{
    const f = ev.target.files[0]
    if(!f) return
    const text = await f.text()
    try{
      const obj = JSON.parse(text)
      nodes.clear(); edges.clear()
      nodes.add(obj.nodes||[])
      edges.add(obj.edges||[])
    }catch(err){ alert('Invalid JSON') }
  })

  // file upload (client-side) - placeholder behaviour: read files and show list
  uploadBtn.addEventListener('click', async ()=>{
    const files = fileInput.files
    if(!files || files.length===0) return alert('Select files to upload')
    for(const f of files){
      const li = document.createElement('li')
      li.textContent = f.name
      const btn = document.createElement('button')
      btn.textContent = 'Index'
      btn.className = 'secondary'
      btn.addEventListener('click', async ()=>{
        // placeholder: send file to /api/upload (multipart/form-data)
        const fd = new FormData(); fd.append('file', f)
        appendChat('user', `Uploading ${f.name}...`)
        try{
    const res = await fetch('/api/upload/',{method:'POST',body:fd})
          const json = await res.json()
          appendChat('bot', json?.message || 'Uploaded')
        }catch(err){
          appendChat('bot', 'Upload failed (placeholder)')
        }
      })
      li.appendChild(btn)
      docList.appendChild(li)
    }
    // clear selected files
    fileInput.value = ''
  })

  // query/chat
  function appendChat(cls, text){
    const d = document.createElement('div'); d.className = 'msg '+cls; d.textContent = text
    chatLog.appendChild(d); chatLog.scrollTop = chatLog.scrollHeight
  }

  sendQueryBtn.addEventListener('click', async ()=>{
    const query = queryInput.value.trim()
    if (!query) return
    
    appendChat('user', query)
    queryInput.value = ''
    output.textContent = 'Searching...'
    
    try {
      // Search entities in local database
      console.log('[frontend] sending search to', `${ENDPOINTS.SEARCH}?q=${encodeURIComponent(query)}`)
      const res = await fetch(`${ENDPOINTS.SEARCH}?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      
      // Clear existing visualization
      nodes.clear()
      edges.clear()
      
      if (data.nodes && data.nodes.length > 0) {
        // Add nodes with proper styling
        const visNodes = data.nodes.map(node => ({
          id: node.id,
          label: node.label || node.id,
          color: {
            background: node.highlight ? '#ff7675' : '#7c3aed',
            border: node.highlight ? '#ff5f5f' : '#6c2aed'
          },
          font: { color: '#ffffff' },
          title: `Type: ${node.type || 'Entity'}`,
          physics: true,
          shape: 'dot',
          size: node.highlight ? 20 : 15
        }))
        nodes.add(visNodes)
        // If any node is highlighted, focus on it
        const highlighted = visNodes.find(n => n.color && n.color.background && n.color.background === '#ff7675');
        if (highlighted) {
          try {
            network.selectNodes([highlighted.id]);
            network.focus(highlighted.id, { scale: 1.6, animation: true });
          } catch(e) { console.warn('focus failed', e); }
        }
        
        // Add relationships with proper styling
        if (data.relations && data.relations.length > 0) {
          const visEdges = data.relations.map(rel => ({
            from: rel.source,
            to: rel.target,
            label: rel.relation || 'related_to',
            arrows: 'to',
            smooth: {
              type: 'continuous',
              roundness: 0.5
            },
            color: {
              color: '#6c2aed',
              highlight: '#ff5f5f'
            },
            width: 2,
            font: { 
              color: '#e6eef8',
              size: 12,
              strokeWidth: 2
            }
          }))
          edges.add(visEdges)
        }

        // Improve visualization
        network.fit({
          animation: {
            duration: 1000,
            easingFunction: 'easeInOutQuad'
          }
        })
        network.stabilize()
        
        appendChat('bot', `Found ${data.nodes.length} matching entities with ${data.relations?.length || 0} relationships`)
        output.textContent = 'Search successful'
      } else {
        appendChat('bot', 'No matching entities found')
        output.textContent = 'No matches found'
      }
    } catch(e) {
      console.error('Search error:', e)
      appendChat('bot', 'Error searching the knowledge graph: ' + e.message)
      output.textContent = 'Search error: ' + e.message
    }
  })

  clearChatBtn.addEventListener('click', ()=>{ chatLog.innerHTML = '' })

  // simple double-click to create edge from selected to clicked
  let fromNode = null
  network.on('doubleClick', params=>{
    if(params.nodes && params.nodes.length>0){
      const nid = params.nodes[0]
      if(!fromNode){ fromNode = nid; appendChat('bot','Selected node '+nid+' (double-click again on a node to connect)') }
      else if(fromNode===nid){ fromNode = null; appendChat('bot','Cleared selection') }
      else{ addEdge(fromNode,nid); fromNode = null; appendChat('bot','Connected nodes') }
    }
  })

  // initial demo nodes
  const a = addNode('Central')
  const b = addNode('Node A')
  const c = addNode('Node B')
  addEdge(a,b); addEdge(a,c)

})();
