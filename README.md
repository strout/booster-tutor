# Booster Tutor
A Discord bot to generate "Magic: the Gathering" boosters

## Usage
The bot responds to the following commands:

`!random`: generates a random pack from the whole history of Magic

`!historic`: generates a random historic pack

`!standard`: generates a random standard pack

`!{setcode}`: generates a pack from the indicated set, available on Arena (e.g., `!znr` generates a Zendikar Rising pack)

`!{setcode}sealed`: generates 6 packs from the indicated set, available on Arena (e.g., `!znrsealed` generates 6 Zendikar Rising packs)

`!chaossealed`: generates 6 random historic packs

`!help`: shows this message

## Under the hood

### Booster data source
All booster data comes from [mtgjson](https://mtgjson.com), an open-source project that catalogs all Magic: The Gathering cards.

### Color balancing
MTG boosters are not purely random, mathematically speaking. They are generated by collating together cards from print sheets in specific orders, this is what is kind of known in the limited world as "print run". How this is performed is not publicly disclosed by Wizards, but in practice the process generates boosters which enforce some properties which are desirable for limited play (like color balancing and no duplicates).

To try to produce boosters which *feel* similar to real MTG boosters, Booster Tutor uses what is known as *Reuben's algorithm*.

> *Reuben's algorithm*
>
> First, generate a booster using a pure random algorithm, then check against the following rules, and if any of the rules aren't met, generate a new booster. Repeat until a booster that conforms to the rules is generated. The rules are:
>
> * A pack must never have more than 4 commons of the same color
> * A pack must have at least 1 common card of each color
> * A pack must have at least 1 common creature
> * A pack must never have more than 2 uncommons of the same color
> * A pack must never have repeated cards

To avoid infinite loops in presence of corner cases, Booster Tutor attempts at balancing packs with *Reuben's algorithm* up to a maximum number of iterations (default: 100).

## Credits

* Part of my implementation is borrowed from [pymtgjson](https://pythonhosted.org/mtgjson)
* Of course, [mtgjson](https://mtgjson.com)
* An interesting discussion over a few approaches to color balancing in MTG boosters from where I took *Reuben's algorithm*: https://gist.github.com/fenhl/8d163733ab92ed718d89975127aac152#simulated-collation
