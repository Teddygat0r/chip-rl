"""Late counter and identity faults that short histories cannot expose."""
NAMES={'crc':('count12','saturating_count','crc_wrap_restart'),'retire':('ticket12','saturating_ticket','numeric_ticket_order')}
def mutate(name,source,fault):
 if fault not in NAMES[name]:raise ValueError('long-history fault')
 if name=='crc':
  marker='next_length=(in_data[32]?0:length)+(WIDTH/8);'
  if fault=='count12':replacement=marker+"next_length=next_length & 16'h0fff;"
  elif fault=='saturating_count':replacement=marker+"if(!in_data[32] && length>65535-(WIDTH/8))next_length=16'hffff;"
  else:
   marker="next_raw=in_data[32]?32'hffffffff:raw;";replacement="next_raw=(in_data[32] || length>65535-(WIDTH/8))?32'hffffffff:raw;"
 else:
  marker='next_ticket<=next_ticket+1;'
  if fault=='ticket12':replacement="next_ticket<=(next_ticket+1)&16'h0fff;"
  elif fault=='saturating_ticket':replacement="next_ticket<=next_ticket==16'hffff ? next_ticket : next_ticket+1;"
  else:marker='tickets[j]==in_data[16+:16]';replacement='tickets[j]==in_data[16+:16] && tickets[j]<next_ticket'
 assert marker in source,(name,fault)
 return source.replace(marker,replacement)
