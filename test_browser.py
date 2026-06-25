from morphos.tools.browser import bm
ctx = bm.ensure()
print('Context:', ctx)
p = ctx.new_page()
print('Page:', p)
p.set_default_timeout(5000)
print('Still page:', p)
