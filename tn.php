<?php
foreach(glob("tn/*") as $f) {
  ?><img title="<?php echo $f ?>" src="<?php echo $f?>"><?php } 
