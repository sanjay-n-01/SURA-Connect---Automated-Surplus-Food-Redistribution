import json

def parse_bp(f, out_f):
    with open(f, 'r', encoding='utf-8') as file:
        d = json.load(file)
        
        with open(out_f, 'a', encoding='utf-8') as out:
            out.write(f'--- {f} ---\n')
            out.write(f"Name: {d.get('name')}\n")
            flow = d.get('flow', [])
            
            def traverse(nodes, prefix=''):
                if not nodes: return
                for node in nodes:
                    out.write(f"{prefix}ID: {node.get('id')}, Module: {node.get('module')}\n")
                    out.write(f"{prefix}Mapper: {json.dumps(node.get('mapper'), ensure_ascii=False)}\n")
                    if 'filter' in node:
                        out.write(f"{prefix}Filter: {json.dumps(node.get('filter'), ensure_ascii=False)}\n")
                    if 'routes' in node:
                        for i, r in enumerate(node['routes']):
                            out.write(f"{prefix}Route {i} filter: {json.dumps(r.get('filter'), ensure_ascii=False)}\n")
                            if 'flow' in r:
                                traverse(r['flow'], prefix+'  ')
            
            traverse(flow)
            out.write('====================\n')

# clear output file first
open('parsed_output.txt', 'w', encoding='utf-8').close()
parse_bp('Integration Webhooks.blueprint.json', 'parsed_output.txt')
parse_bp('NGOresponse Handler.blueprint.json', 'parsed_output.txt')
