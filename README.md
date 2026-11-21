# E-Commerce Inteligente

Projeto acadêmico da disciplina **Implementação de Bancos de Dados NoSQL**, baseado no **Estudo de Caso 01 — E-Commerce Inteligente & Motor de Recomendação**, do professor Ricardo Roberto de Lima.

Uma loja de eletrônicos fictícios com catálogo, carrinho, recomendações e checkout, usando **Python, Streamlit, MongoDB, Redis e Neo4j reais**. Sem pagamento, API intermediária, Docker ou IA generativa. Os SVGs locais são ilustrações vetoriais dos produtos, sem dependência de serviços de imagens.

**Estado da entrega em 21/11/2026:** implementação das seis etapas concluída e suíte completa aprovada: **10 testes, sem falhas ou testes ignorados**. MongoDB, Redis e Neo4j conectaram com sucesso. O grafo de demonstração foi carregado e recomendações, avaliações e checkout foram verificados com os três servidores reais.

## Arquitetura e responsabilidades

```text
Streamlit (app.py + pages/)
           |
      services/ (regras da aplicação)
           |
      database/ (drivers oficiais)
       /          |          \
   MongoDB      Redis       Neo4j
```

| Banco / biblioteca | Dados e função |
| --- | --- |
| MongoDB / PyMongo | Produtos com especificações flexíveis, clientes de demonstração e pedidos com histórico do comprador, preços e quantidades. |
| Redis / redis-py | Tokens temporários, carrinhos separados por sessão, cache de consultas com TTL. |
| Neo4j / driver `neo4j` | Nós Cliente, Produto, Categoria; COMPROU, AVALIOU, PERTENCE_A; recomendações por afinidade entre clientes. |

**Persistência poliglota** significa escolher modelos de dados diferentes conforme o problema. A aplicação usa os três diretamente; não há banco simulado em produção. Mocks existem somente nos testes de falhas e em um teste de navegação, identificados explicitamente.

## Instalação no macOS

Use Python 3.14 (versão instalada e utilizada neste projeto). Se necessário, instale com `brew install python@3.14`.

```bash
git clone https://github.com/Devjv10/ProjetoE-commerce.git
cd ProjetoE-commerce
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

Se o `.env` ainda não existir:

```bash
cp .env.example .env
```

Edite `.env` com suas conexões. Não sobrescreva um `.env` já configurado. As variáveis exportadas no terminal têm prioridade sobre o arquivo. Reinicie o Streamlit após alterações.

### Preparar os servidores

Instalar os drivers Python não instala os servidores.

1. **MongoDB:** instale e inicie o Community Server pelo [guia oficial macOS](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-os-x/). A configuração local usual é `mongodb://localhost:27017`. Atlas também funciona com sua URI.
2. **Redis:** `brew install redis` e `brew services start redis`, conforme o [guia oficial](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-mac-os/). URL local: `redis://localhost:6379/0`.
3. **Neo4j:** no [Neo4j Desktop](https://neo4j.com/docs/desktop/current/installation/), crie e inicie uma instância **Neo4j 5.7 ou superior**, defina a senha e copie a URI Bolt. Preencha `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` e `NEO4J_DATABASE`. AuraDB também pode ser usado com `neo4j+s://...`.

As senhas ficam apenas no `.env`, ignorado pelo Git. Nenhuma credencial do documento do professor foi copiada. `requirements.txt` declara faixas de dependências diretas; `requirements-lock.txt` registra as versões instaladas.

### Carregar os dados

Com os três servidores iniciados e o `.env` configurado:

```bash
python -m scripts.check_connections
python -m scripts.seed_all
```

Ou, individualmente e nesta ordem:

```bash
python -m scripts.seed_mongodb
python -m scripts.seed_redis
python -m scripts.seed_neo4j
```

As cargas podem ser repetidas: MongoDB usa IDs estáveis e `upsert`; Neo4j usa constraints e `MERGE`; Redis aquece o cache e renova um marcador com TTL. Não apagam pedidos ou carrinhos existentes. A carga MongoDB restaura os 12 produtos fictícios e muda a revisão do catálogo, invalidando o cache anterior. A carga Neo4j preserva notas já alteradas pelo usuário (`ON CREATE SET`).

### Abrir o sistema

```bash
python -m streamlit run app.py
```

Abra o endereço exibido no terminal (normalmente `http://localhost:8501`). Na barra lateral, escolha **Ana Lima** e clique em **Iniciar sessão**. As quatro páginas ficam na navegação lateral. O diagnóstico dos bancos está em um expansor na mesma barra.

## Como usar

- **Catálogo:** 12 cards com ilustração, nome, marca, categoria, preço e detalhes. Busca literal por nome e filtro por categoria. O botão adiciona uma unidade ao carrinho.
- **Carrinho:** altere a quantidade e clique em Atualizar; remova produtos ou esvazie o carrinho. O total usa preços em centavos, evitando arredondamentos de ponto flutuante no cálculo.
- **Recomendações:** veja sugestões calculadas em Cypher e registre avaliações de 1 a 5. Compras ou notas 4–5 indicam afinidade; produtos já comprados e produtos avaliados com nota 1–2 são excluídos das sugestões.
- **Checkout:** confira itens e valores e confirme a compra. Pedidos anteriores e operações interrompidas aparecem abaixo para retomada.

Troque o cliente encerrando a sessão e iniciando outra. Cada login cria um carrinho separado, mesmo para o mesmo cliente. Navegar pelas páginas preserva a sessão; recarregar completamente o navegador pode perder o token guardado no estado do Streamlit. Compras pendentes continuam recuperáveis pela identificação do mesmo cliente.

A seleção de clientes é uma identificação para demonstração, **não autenticação segura para uma loja pública**.

## Estrutura do código

```text
app.py                         Entrada e navegação lateral
config.py                      Configuração pelo ambiente
pages/
  catalog.py                   Catálogo e busca
  cart_page.py                 Carrinho
  recommendations_page.py      Recomendações e avaliações
  checkout_page.py              Checkout e retomada
services/
  products.py                  MongoDB, cache e formatação monetária
  cart.py                      Tokens, carrinho, congelamento e limpeza
  recommendations.py           Consultas Cypher e gravação no grafo
  checkout.py                  Etapas retomáveis do pedido
  health.py                    Diagnóstico das conexões
  ui.py                        Componentes visuais compartilhados
database/                      Clientes PyMongo, Redis e Neo4j
scripts/                       Cargas idempotentes e diagnóstico
data/                          Produtos e clientes de entrada em JSON
assets/                        12 ilustrações SVG locais
tests/                         Interface, integração e falhas provocadas
```

Os JSONs são utilizados **somente na carga**. A interface não lê os arquivos como substituto dos bancos.

## Modelagem e consultas para demonstrar

### MongoDB

O produto usa ID estável, preço inteiro em centavos e `especificacoes` como documento flexível. MongoDB armazena documentos em BSON; os dados de carga estão em JSON.

```javascript
// mongosh
use ecommerce_inteligente
// Produtos e especificações flexíveis
db.produtos.find({categoria: "Computadores"})
db.produtos.find({nome: {$regex: "Notebook", $options: "i"}})
// Histórico completo do comprador
db.pedidos.find({cliente_id: "c01"}).sort({criado_em: -1})
db.pedidos.find({status: {$ne: "concluido"}})
db.produtos.getIndexes()
db.pedidos.getIndexes()
```

Índices: `_id` único automático; categoria e nome em produtos; cliente/data e status em pedidos. Busca por trecho com regex sem prefixo pode varrer documentos: é aceitável para 12 produtos; o índice de nome não torna toda busca por substring eficiente.

### Redis

| Chave | Conteúdo | Expiração |
| --- | --- | --- |
| `ecommerce:session:<hash>` | Cliente, nome e ID da sessão | 1 hora sem atividade; renovada ao usar |
| `ecommerce:cart:<sessao>` | ID do carrinho, itens e estado | 24 horas após alteração |
| `ecommerce:products:<revisao>:<hash>` | Resultado JSON de busca/filtro | 60 segundos |
| `ecommerce:demo:info` | Marcador da carga | 24 horas |

O token aleatório fica no estado da interface; sua chave Redis usa SHA-256. O carrinho é um JSON por sessão. `WATCH` + `MULTI/EXEC` evita sobrescrever alterações concorrentes. Um carrinho em checkout fica congelado **sem TTL** até a conclusão, para preservar o retrato durante falhas.

```bash
redis-cli --scan --pattern 'ecommerce:products:*'
redis-cli --scan --pattern 'ecommerce:cart:*'
redis-cli --scan --pattern 'ecommerce:session:*'
# Substitua pela chave encontrada, sem os sinais < >:
redis-cli TTL '<chave>'
redis-cli GET '<chave>'
```

Consultas repetidas usam o cache. Cada consulta lê a pequena revisão do catálogo no MongoDB e usa essa revisão na chave Redis. Reexecutar a carga muda a revisão; chaves antigas deixam de ser usadas e expiram naturalmente. Essa estratégia continua correta se Redis estiver fora durante a carga. Toda futura rotina que modificar produtos deverá atualizar a revisão também. Se Redis cair, o catálogo consulta o MongoDB; carrinho e login não fingem sucesso.

### Neo4j

```cypher
// Modelo e visualização
MATCH (c:Cliente)-[r:COMPROU|AVALIOU]->(p:Produto)-[:PERTENCE_A]->(cat:Categoria)
RETURN c, r, p, cat LIMIT 60;

// Compras de Ana
MATCH (:Cliente {id: 'c01'})-[r:COMPROU]->(p:Produto)
RETURN p.nome, r.pedido_id, r.quantidade;

// Recomendação cruzada simplificada
MATCH (eu:Cliente {id: 'c01'})-[:COMPROU]->(comum:Produto)<-[:COMPROU]-(outro:Cliente)
MATCH (outro)-[:COMPROU]->(sugestao:Produto)
WHERE outro <> eu AND NOT EXISTS { MATCH (eu)-[:COMPROU]->(sugestao) }
RETURN sugestao.nome, count(DISTINCT outro) AS clientes_similares
ORDER BY clientes_similares DESC;

SHOW CONSTRAINTS;
```

A consulta completa em `services/recommendations.py` também considera avaliações positivas, exclui avaliações negativas e retorna interesses comuns para explicar cada sugestão. Os históricos são dados fictícios de entrada; as recomendações não são listas prontas em Python.

`Cliente.id`, `Produto.id`, `Categoria.nome` e `COMPROU.evento_id` têm unicidade. O evento de compra combina ID do pedido e ID do produto; `MERGE` e a constraint impedem duplicar a relação nas retentativas. `AVALIOU` mantém uma nota por par cliente/produto nas operações sequenciais da demonstração.

## Checkout e tratamento de falhas

Não existe transação única abrangendo os três bancos. O projeto usa uma sequência retomável, com estados persistidos:

```text
Redis: congela carrinho e resumo (ID estável)
  → MongoDB: pendente_grafo (upsert por _id)
  → Neo4j: registra COMPROU (MERGE por evento único)
  → MongoDB: pendente_limpeza
  → Redis: apaga somente o carrinho cujo ID corresponde ao pedido
  → MongoDB: concluido
```

- Se MongoDB falhar antes da gravação, o resumo congelado continua no Redis e pode ser recuperado na lista de pendências.
- Se Neo4j falhar, o pedido fica `pendente_grafo`; o carrinho permanece intacto.
- Se a limpeza Redis falhar, o pedido fica `pendente_limpeza`; retomar não repete a etapa do grafo.
- Se a resposta se perder após uma gravação, a retentativa reutiliza o ID. `_id` único, transições condicionais e `MERGE` evitam criar outro pedido.
- A limpeza Redis compara IDs atomicamente com Lua. Retomar um pedido antigo não apaga um novo carrinho.
- Um novo login do mesmo cliente encontra pedidos e rascunhos pendentes. A varredura de rascunhos com `SCAN` é adequada ao volume acadêmico.

A recuperação exige que os dados dos servidores sejam preservados. Para sobreviver também à reinicialização do Redis, configure persistência AOF/RDB no servidor; disponibilidade temporária e destruição de dados são problemas diferentes. Carrinhos comuns têm expiração intencional. A aplicação não implementa pagamento, estoque, estorno ou transações distribuídas.

## Testes

```bash
# Sintaxe e dependências
python -m compileall -q app.py config.py database services scripts pages tests
python -m pip check

# Testes de interface sem servidores (integração aparece como skipped)
python -m unittest discover -s tests -v

# MongoDB e Redis reais; falhas do grafo são injetadas em testes específicos
RUN_INTEGRATION=1 python -m unittest discover -s tests -v

# Inclui recomendação, avaliação e checkout com os três bancos reais
RUN_INTEGRATION=1 RUN_NEO4J_TESTS=1 python -m unittest discover -s tests -v
```

Os testes MongoDB/Redis criam banco e prefixo exclusivos `test_<uuid>` e os removem no fim. O teste completo Neo4j exige um grafo **de desenvolvimento**: carrega os nós de demonstração idempotentemente e usa dois clientes temporários, removidos ao final. Não executá-lo contra dados de produção.

Os testes cobrem busca literal, filtro, TTL, invalidação, isolamento de sessões, alterações concorrentes, quantidades, remoção, sessão inválida, falhas provocadas, retomada, proteção de carrinho novo e navegação das quatro páginas. AppTest executa a interface, mas não substitui inspeção visual em navegador.

### Resultado efetivamente executado

Em 21/11/2026, `RUN_INTEGRATION=1 RUN_NEO4J_TESTS=1 python -m unittest discover -s tests -v` terminou com **10 testes aprovados, sem testes ignorados**. O diagnóstico confirmou os três bancos e a carga Neo4j criou constraints, nós e relacionamentos.

O teste integrado real confirmou recomendações baseadas em compras em comum, exclusão de sugestão após avaliação negativa, pedido concluído, compra no grafo sem duplicação na retentativa e carrinho vazio. O teste de navegação percorreu as quatro páginas com resposta do grafo simulada; essa verificação é complementar ao teste real. Os testes de recuperação injetam falhas deliberadas. A compilação Python e `pip check` passaram durante o desenvolvimento. Não houve inspeção visual em navegador. Antes da apresentação, mantenha os três servidores ativos e ensaie o roteiro abaixo.

## Desenvolvimento explicado por etapa

| Etapa | Arquivos principais e implementação | Como testar / o que explicar |
| --- | --- | --- |
| 1 | `config.py`, `database/`, `health.py`, `.env.example`: conexões e diagnóstico | Executar `scripts.check_connections`. Driver é cliente; servidor é o banco separado. |
| 2 | `data/`, `assets/`, `products.py`, `catalog.py`, `seed_mongodb.py`: catálogo real | Carregar MongoDB, buscar Notebook e filtrar Áudio. Documentos permitem especificações diferentes. |
| 3 | `cart.py`, `cart_page.py`, `seed_redis.py`, cache em `products.py` | Criar sessão, alterar quantidades, navegar; repetir busca e inspecionar TTL. Redis guarda estado por chave e cache temporário. |
| 4 | `recommendations.py`, `recommendations_page.py`, `seed_neo4j.py` | Carregar o grafo; selecionar Ana; avaliar e comparar clientes. Cypher percorre relações em comum, não uma lista fixa. |
| 5 | `checkout.py`, `checkout_page.py` | Confirmar, consultar pedido e COMPROU; observar carrinho vazio. Explicar ID estável e os estados retomáveis. |
| 6 | `tests/`, README e versões fixadas | Rodar as suítes e revisar o roteiro. Distinguir testes reais de falhas simuladas. |

## Roteiro para uma defesa de até 10 minutos

1. **0–1 min:** apresentar o problema e a persistência poliglota.
2. **1–3 min:** mostrar documento de produto, chave do carrinho e modelo do grafo.
3. **3–5 min:** identificar Ana, buscar Notebook, adicionar um produto, alterar quantidade e mostrar TTL do cache.
4. **5–7 min:** mostrar recomendações, explicar um interesse em comum e registrar uma nota.
5. **7–9 min:** confirmar checkout; consultar pedido MongoDB, COMPROU Neo4j e carrinho Redis limpo.
6. **9–10 min:** explicar recuperação de falhas e mostrar resultado dos testes.

O documento declara limite de 10 minutos, mas o roteiro detalhado sugerido soma mais. Confirme a duração com o professor. Cada integrante deve saber explicar as três tecnologias e o caminho de um pedido.

## Perguntas prováveis do professor

- **Por que MongoDB para catálogo?** As especificações variam entre notebook, fone e smartphone; documentos acomodam essa variação.
- **JSON e BSON são iguais?** JSON é o formato textual de entrada; BSON é a representação binária usada pelo MongoDB, com tipos adicionais.
- **Por que Redis?** Acesso rápido por chave e expiração nativa servem bem a sessão, carrinho e cache.
- **O TTL é toda a invalidação?** Não. TTL limita a duração; a revisão do catálogo invalida imediatamente a reutilização após atualizações feitas pela carga.
- **Há consulta MongoDB mesmo com cache?** Sim, para a revisão; o resultado completo e filtros de produtos vêm do Redis em um cache hit.
- **Como impedir que dois cliques percam quantidades?** `WATCH` detecta concorrência; a transação repete a leitura antes de gravar.
- **Como funciona a recomendação?** Clientes compartilham produtos comprados ou avaliados positivamente. Produtos comprados por esses clientes são candidatos, excluindo os já comprados e rejeitados.
- **O que é Index-Free Adjacency?** O grafo mantém conexões entre nós para navegar por relacionamentos sem fazer um join tabular a cada salto; índices ajudam a localizar o ponto inicial.
- **Por que não usar IA generativa?** A recomendação exigida é baseada em relações e consultas Cypher; não depende de modelos ou APIs pagas.
- **E se Neo4j cair no checkout?** O pedido fica pendente no MongoDB, e o carrinho preservado permite retomar.
- **Isso é uma transação ACID entre os três bancos?** Não. É um fluxo com estados e operações idempotentes, com consistência eventual durante falhas.
- **Como evitar duplicar pedido?** O ID nasce no carrinho, vira `_id` do pedido e é reutilizado em todas as retentativas.
- **Pode abrir essa loja publicamente?** Não como está: identificação por seleção é apenas para apresentação e não autentica pessoas.

Referências técnicas consultadas: [Streamlit navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation), [transações redis-py](https://redis.io/docs/latest/develop/clients/redis-py/transpipe/), [PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/get-started/) e [driver Neo4j](https://neo4j.com/docs/python-manual/current/connect/). A referência de requisitos é o documento do professor fornecido pelo usuário.
